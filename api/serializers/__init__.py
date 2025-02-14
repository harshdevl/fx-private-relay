from django.contrib.auth.models import User
from django.db.models import prefetch_related_objects

from rest_framework import serializers, exceptions
from waffle import get_waffle_flag_model

from emails.models import DomainAddress, Profile, RelayAddress


class PremiumValidatorsMixin:
    # the user must be premium to set block_list_emails=True
    def validate_block_list_emails(self, value):
        if not value:
            return value
        user = self.context["request"].user
        prefetch_related_objects([user], "socialaccount_set", "profile")
        if not user.profile.has_premium:
            raise exceptions.AuthenticationFailed(
                "Must be premium to set block_list_emails."
            )
        return value


class RelayAddressSerializer(PremiumValidatorsMixin, serializers.ModelSerializer):
    mask_type = serializers.CharField(default="random", read_only=True, required=False)

    class Meta:
        model = RelayAddress
        fields = [
            "mask_type",
            "enabled",
            "description",
            "generated_for",
            "block_list_emails",
            "used_on",
            # read-only
            "id",
            "address",
            "domain",
            "full_address",
            "created_at",
            "last_modified_at",
            "last_used_at",
            "num_forwarded",
            "num_blocked",
            "num_level_one_trackers_blocked",
            "num_replied",
            "num_spam",
        ]
        read_only_fields = [
            "id",
            "mask_type",
            "address",
            "domain",
            "full_address",
            "created_at",
            "last_modified_at",
            "last_used_at",
            "num_forwarded",
            "num_blocked",
            "num_level_one_trackers_blocked",
            "num_replied",
            "num_spam",
        ]


class DomainAddressSerializer(PremiumValidatorsMixin, serializers.ModelSerializer):
    mask_type = serializers.CharField(default="custom", read_only=True, required=False)

    class Meta:
        model = DomainAddress
        fields = [
            "mask_type",
            "enabled",
            "description",
            "block_list_emails",
            "used_on",
            # read-only
            "id",
            "address",
            "domain",
            "full_address",
            "created_at",
            "last_modified_at",
            "last_used_at",
            "num_forwarded",
            "num_blocked",
            "num_level_one_trackers_blocked",
            "num_replied",
            "num_spam",
        ]
        read_only_fields = [
            "id",
            "mask_type",
            "domain",
            "full_address",
            "created_at",
            "last_modified_at",
            "last_used_at",
            "num_forwarded",
            "num_blocked",
            "num_level_one_trackers_blocked",
            "num_replied",
            "num_spam",
        ]


class StrictReadOnlyFieldsMixin:
    """
    Raises a validation error (400) if read only fields are in the body of PUT/PATCH requests.

    This class comes from https://github.com/encode/django-rest-framework/issues/1655#issuecomment-1197033853,
    where different solutions to mitigating 200 response codes in read-only fields are discussed.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if not hasattr(self, "initial_data"):
            return attrs

        # Getting the declared read only fields and read only fields from Meta
        read_only_fields = set(
            field_name for field_name, field in self.fields.items() if field.read_only
        ).union(set(getattr(self.Meta, "read_only_fields", set())))

        # Getting implicit read only fields that are in the Profile model, but were not defined in the serializer.
        # By default, they won't update if put in the body of a request, but they still give a 200 response (which we don't want).
        implicit_read_only_fields = set(
            field for field in vars(self.Meta.model) if field not in self.fields
        )

        received_read_only_fields = set(self.initial_data).intersection(
            read_only_fields.union(implicit_read_only_fields)
        )

        if received_read_only_fields:
            errors = {}
            for field_name in received_read_only_fields:
                errors[field_name] = serializers.ErrorDetail(
                    "This field is read only", code="read_only"
                )

            raise serializers.ValidationError(errors)

        return attrs


class ProfileSerializer(StrictReadOnlyFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id",
            "server_storage",
            "store_phone_log",
            "subdomain",
            "has_premium",
            "has_phone",
            "has_vpn",
            "onboarding_state",
            "date_subscribed",
            "avatar",
            "next_email_try",
            "bounce_status",
            "api_token",
            "emails_blocked",
            "emails_forwarded",
            "emails_replied",
            "level_one_trackers_blocked",
            "remove_level_one_email_trackers",
            "total_masks",
            "at_mask_limit",
        ]
        read_only_fields = [
            "id",
            "subdomain",
            "has_premium",
            "has_phone",
            "has_vpn",
            "date_subscribed",
            "avatar",
            "next_email_try",
            "bounce_status",
            "api_token",
            "emails_blocked",
            "emails_forwarded",
            "emails_replied",
            "level_one_trackers_blocked",
            "total_masks",
            "at_mask_limit",
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]
        read_only_fields = ["email"]


class FlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_waffle_flag_model()
        fields = [
            "id",
            "name",
            "everyone",
            "note",
        ]
        read_only_fields = [
            "id",
        ]

    def validate_everyone(self, value):
        """
        Turn False into None. This disables the flag for most, but allows users
        and groups to still have the flag. Setting the flag to False would also
        disable the flag for those users.
        """
        if value:
            return True
        return None

    def validate(self, data):
        if (data.get("name", "").lower() == "manage_flags") or (
            hasattr(self, "instance")
            and getattr(self.instance, "name", "").lower() == "manage_flags"
        ):
            raise serializers.ValidationError(
                "Changing the `manage_flags` flag is not allowed."
            )
        return super().validate(data)


class WebcompatIssueSerializer(serializers.Serializer):
    issue_on_domain = serializers.URLField(
        max_length=200, min_length=None, allow_blank=False
    )
    user_agent = serializers.CharField(required=False, default="", allow_blank=True)
    email_mask_not_accepted = serializers.BooleanField(required=False, default=False)
    add_on_visual_issue = serializers.BooleanField(required=False, default=False)
    email_not_received = serializers.BooleanField(required=False, default=False)
    other_issue = serializers.CharField(required=False, default="", allow_blank=True)


class FirstForwardedEmailSerializer(serializers.Serializer):
    mask = serializers.EmailField(required=True)
