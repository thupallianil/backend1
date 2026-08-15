from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.models import BusinessProfile
from .serializers import ProfileSerializer


def get_user_profile(user):
    profile = BusinessProfile.objects.filter(owner=user).first()
    if not profile:
        profile = BusinessProfile.objects.first()
    if not profile:
        profile = BusinessProfile.objects.create(
            owner=user,
            business_name=user.username or user.email or "My Business",
            email=user.email or "",
        )
    return profile


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_detail(request):
    profile = get_user_profile(request.user)

    if request.method == "GET":
        return Response({
            "success": True,
            "data": ProfileSerializer(profile, context={"request": request}).data,
        })

    data = request.data.copy()
    if "website" in data:
        web_val = str(data["website"] or "").strip()
        if web_val and not web_val.startswith("http://") and not web_val.startswith("https://"):
            data["website"] = "https://" + web_val

    serializer = ProfileSerializer(
        profile,
        data=data,
        partial=True,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response({
        "success": True,
        "message": "Profile updated successfully",
        "data": serializer.data,
    })


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_update(request):
    profile = get_user_profile(request.user)

    data = request.data.copy()
    if "website" in data:
        web_val = str(data["website"] or "").strip()
        if web_val and not web_val.startswith("http://") and not web_val.startswith("https://"):
            data["website"] = "https://" + web_val

    serializer = ProfileSerializer(
        profile,
        data=data,
        partial=True,
        context={"request": request},
    )

    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response({
        "success": True,
        "message": "Profile updated successfully",
        "data": serializer.data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def profile_logo(request):
    profile = get_user_profile(request.user)

    if "logo" not in request.FILES:
        return Response({
            "success": False,
            "message": "Logo file is required.",
        }, status=400)

    profile.logo = request.FILES["logo"]
    profile.save()

    return Response({
        "success": True,
        "message": "Logo uploaded successfully",
        "logo": profile.logo.url,
    })