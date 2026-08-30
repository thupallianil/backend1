from decimal import Decimal

from django.db.models import (
    Count,
    Sum,
)
from django.db.models.functions import (
    TruncMonth,
)

from api.models import (
    BusinessProfile,
    Client,
    Quote,
    Invoice,
    Payment,
    Receipt,
)


ZERO = Decimal("0.00")


class ReportService:

    # =========================================================
    # BUSINESS
    # =========================================================

    @staticmethod
    def get_business(user):
        try:
            biz = BusinessProfile.objects.filter(owner=user).first()
            if not biz and (user.is_superuser or getattr(getattr(user, "profile", None), "role", None) == "super_admin"):
                biz = BusinessProfile.objects.first()
            return biz
        except Exception:
            return BusinessProfile.objects.first()

    # =========================================================
    # DASHBOARD
    # =========================================================

    @classmethod
    def dashboard(cls, user, year=None):
        business = cls.get_business(user)

        if not business:
            raise ValueError(
                "Business profile not found for this user."
            )

        clients = Client.objects.filter(
            business=business
        )

        quotes = Quote.objects.filter(
            business=business
        )

        invoices = Invoice.objects.filter(
            business=business
        )

        payments = Payment.objects.filter(
            business=business
        )

        receipts = Receipt.objects.filter(
            business=business
        )
        
        if year:
            clients = clients.filter(created_at__year=year)
            quotes = quotes.filter(issue_date__year=year)
            invoices = invoices.filter(issue_date__year=year)
            payments = payments.filter(paid_at__year=year)
            receipts = receipts.filter(issued_date__year=year)

        invoice_totals = invoices.aggregate(
            total=Sum("total"),
            paid=Sum("paid_amount"),
            balance=Sum("balance_due"),
        )

        payment_totals = payments.filter(
            status=Payment.Status.SUCCESS
        ).aggregate(
            total=Sum("amount")
        )

        return {
            "clients": clients.count(),

            "active_clients": clients.filter(
                is_active=True
            ).count(),

            "quotes": quotes.count(),

            "accepted_quotes": quotes.filter(
                status=Quote.Status.ACCEPTED
            ).count(),

            "invoices": invoices.count(),

            "paid_invoices": invoices.filter(
                status=Invoice.Status.PAID
            ).count(),

            "pending_invoices": invoices.filter(
                status__in=[
                    Invoice.Status.DRAFT,
                    Invoice.Status.SENT,
                    Invoice.Status.PARTIALLY_PAID,
                ]
            ).count(),

            "overdue_invoices": invoices.filter(
                status=Invoice.Status.OVERDUE
            ).count(),

            "invoice_total": (
                invoice_totals["total"]
                or ZERO
            ),

            "paid_amount": (
                invoice_totals["paid"]
                or ZERO
            ),

            "outstanding_amount": (
                invoice_totals["balance"]
                or ZERO
            ),

            "payments": payments.count(),

            "receipts": receipts.count(),

            "payment_total": (
                payment_totals["total"]
                or ZERO
            ),
            
            "revenue_monthly": [
                {
                    "month": m["month"],
                    "revenue": m["sales"],
                }
                for m in cls.sales(user, year=year).get("months", [])
            ],
            
            "payment_monthly": cls.payments(user, year=year).get("months", []),
            
            "tax_breakdown": [
                {
                    "name": "Total GST",
                    "value": cls.tax(user, year=year).get("total_tax", ZERO)
                }
            ],
        }

    # =========================================================
    # SALES REPORT
    # =========================================================

    @classmethod
    def sales(cls, user, year=None):
        business = cls.get_business(user)

        if not business:
            raise ValueError(
                "Business profile not found for this user."
            )

        invoices = Invoice.objects.filter(
            business=business
        )

        if year:
            invoices = invoices.filter(
                issue_date__year=year
            )

        monthly = (
            invoices
            .annotate(
                month=TruncMonth("issue_date")
            )
            .values("month")
            .annotate(
                sales=Sum("total"),
                subtotal=Sum("subtotal"),
                tax=Sum("tax"),
                discount=Sum("discount"),
                invoices=Count("id"),
            )
            .order_by("month")
        )

        months = []

        for row in monthly:
            month = row["month"]

            months.append({
                "month": month.strftime("%b"),
                "date": month.strftime("%Y-%m-%d"),
                "sales": row["sales"] or ZERO,
                "subtotal": row["subtotal"] or ZERO,
                "tax": row["tax"] or ZERO,
                "discount": row["discount"] or ZERO,
                "invoices": row["invoices"],
            })

        totals = invoices.aggregate(
            total_sales=Sum("total"),
            total_subtotal=Sum("subtotal"),
            total_tax=Sum("tax"),
            total_discount=Sum("discount"),
        )

        return {
            "months": months,

            "total_sales": (
                totals["total_sales"]
                or ZERO
            ),

            "total_subtotal": (
                totals["total_subtotal"]
                or ZERO
            ),

            "total_tax": (
                totals["total_tax"]
                or ZERO
            ),

            "total_discount": (
                totals["total_discount"]
                or ZERO
            ),
        }

    # =========================================================
    # PAYMENT REPORT
    # =========================================================

    @classmethod
    def payments(cls, user, year=None):
        business = cls.get_business(user)

        if not business:
            raise ValueError(
                "Business profile not found for this user."
            )

        payments = Payment.objects.filter(
            business=business
        )

        invoices = Invoice.objects.filter(
            business=business
        )

        if year:
            payments = payments.filter(
                paid_at__year=year
            )

            invoices = invoices.filter(
                issue_date__year=year
            )

        monthly_paid = (
            payments
            .filter(
                status=Payment.Status.SUCCESS,
                paid_at__isnull=False,
            )
            .annotate(
                month=TruncMonth("paid_at")
            )
            .values("month")
            .annotate(
                paid=Sum("amount"),
                payment_count=Count("id"),
            )
            .order_by("month")
        )

        paid_by_month = {}

        for row in monthly_paid:
            month = row["month"]

            paid_by_month[
                month.strftime("%Y-%m")
            ] = {
                "month": month.strftime("%b"),
                "date": month.strftime("%Y-%m-%d"),
                "paid": row["paid"] or ZERO,
                "payment_count": row["payment_count"],
            }

        monthly_outstanding = (
            invoices
            .annotate(
                month=TruncMonth("issue_date")
            )
            .values("month")
            .annotate(
                outstanding=Sum("balance_due")
            )
            .order_by("month")
        )

        outstanding_by_month = {}

        for row in monthly_outstanding:
            month = row["month"]

            outstanding_by_month[
                month.strftime("%Y-%m")
            ] = row["outstanding"] or ZERO

        all_months = sorted(
            set(
                paid_by_month.keys()
            )
            |
            set(
                outstanding_by_month.keys()
            )
        )

        months = []

        for key in all_months:
            paid_data = paid_by_month.get(
                key,
                {}
            )

            months.append({
                "month": paid_data.get(
                    "month",
                    key[5:],
                ),

                "date": (
                    key + "-01"
                ),

                "paid": paid_data.get(
                    "paid",
                    ZERO,
                ),

                "outstanding":
                    outstanding_by_month.get(
                        key,
                        ZERO,
                    ),

                "payment_count":
                    paid_data.get(
                        "payment_count",
                        0,
                    ),
            })

        payment_totals = payments.filter(
            status=Payment.Status.SUCCESS
        ).aggregate(
            total=Sum("amount")
        )

        outstanding_total = invoices.aggregate(
            total=Sum("balance_due")
        )

        return {
            "months": months,

            "total_paid": (
                payment_totals["total"]
                or ZERO
            ),

            "total_outstanding": (
                outstanding_total["total"]
                or ZERO
            ),

            "successful_payments": payments.filter(
                status=Payment.Status.SUCCESS
            ).count(),

            "pending_payments": payments.filter(
                status=Payment.Status.PENDING
            ).count(),

            "failed_payments": payments.filter(
                status=Payment.Status.FAILED
            ).count(),
        }

    # =========================================================
    # TAX REPORT
    # =========================================================

    @classmethod
    def tax(cls, user, year=None):
        business = cls.get_business(user)

        if not business:
            raise ValueError(
                "Business profile not found for this user."
            )

        invoices = Invoice.objects.filter(
            business=business
        )

        if year:
            invoices = invoices.filter(
                issue_date__year=year
            )

        total_tax = invoices.aggregate(
            total=Sum("tax")
        )["total"] or ZERO

        monthly_data = (
            invoices
            .annotate(
                month=TruncMonth("issue_date")
            )
            .values("month")
            .annotate(
                tax=Sum("tax")
            )
            .order_by("month")
        )

        monthly = []

        for row in monthly_data:
            month = row["month"]

            monthly.append({
                "month": month.strftime("%b"),
                "date": month.strftime("%Y-%m-%d"),
                "tax": row["tax"] or ZERO,
            })

        return {
            "total_tax": total_tax,

            "monthly": monthly,

            "note": (
                "Tax is stored as an aggregate invoice tax "
                "amount. The database does not contain "
                "separate CGST, SGST and IGST fields."
            ),
        }

    # =========================================================
    # CLIENT REPORT
    # =========================================================

    @classmethod
    def clients(cls, user):
        business = cls.get_business(user)

        if not business:
            raise ValueError(
                "Business profile not found for this user."
            )

        queryset = Client.objects.filter(
            business=business
        )

        total_clients = queryset.count()

        active_clients = queryset.filter(
            is_active=True
        ).count()

        inactive_clients = queryset.filter(
            is_active=False
        ).count()

        top_clients = (
            queryset
            .annotate(
                invoice_count=Count(
                    "invoices"
                ),
                invoice_total=Sum(
                    "invoices__total"
                ),
            )
            .order_by(
                "-invoice_total"
            )[:10]
        )

        data = []

        for client in top_clients:
            data.append({
                "id": client.id,

                "name": client.name,

                "company_name":
                    client.company_name,

                "invoice_count":
                    client.invoice_count,

                "invoice_total":
                    client.invoice_total
                    or ZERO,

                "is_active":
                    client.is_active,
            })

        return {
            "total_clients": total_clients,

            "active_clients":
                active_clients,

            "inactive_clients":
                inactive_clients,

            "top_clients": data,
        }

    # =========================================================
    # PROFIT / LOSS
    # =========================================================

    @classmethod
    def profit_loss(cls, user, year=None):
        business = cls.get_business(user)

        if not business:
            raise ValueError(
                "Business profile not found for this user."
            )

        invoices = Invoice.objects.filter(
            business=business
        )

        if year:
            invoices = invoices.filter(
                issue_date__year=year
            )

        totals = invoices.aggregate(
            revenue=Sum("total"),
            discount=Sum("discount"),
            tax=Sum("tax"),
            collected=Sum("paid_amount"),
            outstanding=Sum("balance_due"),
        )

        revenue = totals["revenue"] or ZERO
        discounts = totals["discount"] or ZERO
        tax = totals["tax"] or ZERO
        collected = totals["collected"] or ZERO
        outstanding = totals["outstanding"] or ZERO

        # There is currently no Expense model in api/models.py.
        expenses = ZERO

        # Do not pretend that this is accounting profit.
        # This represents invoice revenue because expenses
        # are not stored in the current database schema.
        net_profit = revenue - expenses

        return {
            "revenue": revenue,

            "collected": collected,

            "outstanding": outstanding,

            "discounts": discounts,

            "tax": tax,

            "expenses": expenses,

            "net_profit": net_profit,

            "note": (
                "Expenses are currently unavailable because "
                "the database does not contain an Expense model. "
                "Net profit therefore represents revenue before "
                "expenses, not final accounting profit."
            ),
        }