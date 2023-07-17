from datetime import datetime, timezone, timedelta
from io import StringIO
from typing import Iterator
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.conf import settings

from allauth.socialaccount.models import SocialAccount
from model_bakery import baker
from pytest_django.fixtures import SettingsWrapper
import pytest

if settings.PHONES_ENABLED:
    from ..models import InboundContact, RealPhone, RelayNumber

pytestmark = pytest.mark.skipif(
    not settings.PHONES_ENABLED, reason="PHONES_ENABLED is False"
)
THE_COMMAND = "delete_phone_data"


@pytest.fixture(autouse=True)
def test_settings(settings: SettingsWrapper) -> SettingsWrapper:
    """Override settings for tests"""
    settings.SUBSCRIPTIONS_WITH_PHONE = ["PHONE_SUBSCRIPTION"]
    return settings


@pytest.fixture(autouse=True)
def mock_twilio_client() -> Iterator[Mock]:
    """Mock PhonesConfig with a mock twilio client"""
    with patch("phones.apps.PhonesConfig.twilio_client") as mock_twilio_client:
        yield mock_twilio_client


@pytest.fixture
def phone_user(db: None, test_settings: SettingsWrapper) -> User:
    """Return a Relay user with phone setup and phone usage."""
    # Create the user
    now = datetime.now(tz=timezone.utc)
    phone_user = baker.make(User, email="phone_user@example.com")
    phone_user.profile.date_subscribed = now - timedelta(days=15)
    phone_user.profile.save()

    # Add FxA with phone subscription
    baker.make(
        SocialAccount,
        user=phone_user,
        provider="fxa",
        uid="decd14f50fce4865b0fd06afcd9d2c4d",
        extra_data={
            "avatar": "http://avatar.example.com/avatar.jpg",
            "subscriptions": [settings.SUBSCRIPTIONS_WITH_PHONE[0]],
        },
    )

    # Add confirmed real phone
    baker.make(
        RealPhone,
        user=phone_user,
        number="+12005550123",
        verification_sent_date=now - timedelta(days=14),
        verified=True,
    )

    # Add relay phone mask
    relay_number = baker.make(RelayNumber, user=phone_user, number="+13015550123")

    # Add SMS and Voice contacts
    baker.make(
        InboundContact,
        relay_number=relay_number,
        inbound_number="+14035550123",
        last_inbound_type="text",
        num_texts=1,
        last_inbound_date=now - timedelta(days=12),
        last_text_date=now - timedelta(days=12),
    )
    baker.make(
        InboundContact,
        relay_number=relay_number,
        inbound_number="+14045550123",
        last_inbound_type="call",
        num_calls=1,
        last_inbound_date=now - timedelta(days=10),
        last_call_date=now - timedelta(days=10),
    )

    return phone_user


def test_active_user(phone_user: User) -> None:
    """A user's real phone, relay phone, and inbound contacts are deleted."""
    assert RealPhone.objects.filter(user=phone_user).exists()
    relay_number = RelayNumber.objects.get(user=phone_user)
    assert InboundContact.objects.filter(relay_number=relay_number).count() == 2

    stdout = StringIO()
    call_command(THE_COMMAND, phone_user.profile.fxa.uid, stdout=stdout)

    expected_stdout = f"""\
Found a matching user:

* FxA ID: decd14f50fce4865b0fd06afcd9d2c4d
* User ID: {phone_user.id}
* Email: phone_user@example.com
* Real Phone: +12005550123
* Relay Phone: +13015550123
* Inbound Contacts: 2

Deleted user's phone data.
"""
    assert stdout.getvalue() == expected_stdout

    phone_user.refresh_from_db()
    assert phone_user.profile.has_phone
    assert not RealPhone.objects.filter(user=phone_user).exists()
    assert not RelayNumber.objects.filter(user=phone_user).exists()
    assert not InboundContact.objects.filter(relay_number=relay_number).exists()


def test_no_contacts(phone_user: User) -> None:
    """A user's real phone and relay phone are deleted, even without contacts."""
    relay_number = RelayNumber.objects.get(user=phone_user)
    InboundContact.objects.filter(relay_number=relay_number).delete()

    stdout = StringIO()
    call_command(THE_COMMAND, phone_user.profile.fxa.uid, stdout=stdout)

    expected_stdout = f"""\
Found a matching user:

* FxA ID: decd14f50fce4865b0fd06afcd9d2c4d
* User ID: {phone_user.id}
* Email: phone_user@example.com
* Real Phone: +12005550123
* Relay Phone: +13015550123
* Inbound Contacts: 0

Deleted user's phone data.
"""
    assert stdout.getvalue() == expected_stdout

    phone_user.refresh_from_db()
    assert phone_user.profile.has_phone
    assert not RealPhone.objects.filter(user=phone_user).exists()
    assert not RelayNumber.objects.filter(user=phone_user).exists()
    assert not InboundContact.objects.filter(relay_number=relay_number).exists()


def test_no_relay_phone(phone_user: User) -> None:
    """A user's real phone is deleted, even without a relay phone setup."""
    RelayNumber.objects.filter(user=phone_user).delete()

    stdout = StringIO()
    call_command(THE_COMMAND, phone_user.profile.fxa.uid, stdout=stdout)

    expected_stdout = f"""\
Found a matching user:

* FxA ID: decd14f50fce4865b0fd06afcd9d2c4d
* User ID: {phone_user.id}
* Email: phone_user@example.com
* Real Phone: +12005550123
* Relay Phone: <NO RELAY PHONE>
* Inbound Contacts: 0

Deleted user's phone data.
"""
    assert stdout.getvalue() == expected_stdout

    phone_user.refresh_from_db()
    assert phone_user.profile.has_phone
    assert not RealPhone.objects.filter(user=phone_user).exists()


def test_no_real_phone(phone_user: User) -> None:
    """Nothing is done if a user doesn't have a real phone setup."""
    RelayNumber.objects.filter(user=phone_user).delete()
    RealPhone.objects.filter(user=phone_user).delete()

    stdout = StringIO()
    call_command(THE_COMMAND, phone_user.profile.fxa.uid, stdout=stdout)

    expected_stdout = f"""\
Found a matching user:

* FxA ID: decd14f50fce4865b0fd06afcd9d2c4d
* User ID: {phone_user.id}
* Email: phone_user@example.com
* Real Phone: <NO REAL PHONE>
* Relay Phone: <NO RELAY PHONE>
* Inbound Contacts: 0

No action taken, since the user has no phone data.
"""
    assert stdout.getvalue() == expected_stdout

    phone_user.refresh_from_db()
    assert phone_user.profile.has_phone
    assert not RealPhone.objects.filter(user=phone_user).exists()


@pytest.mark.django_db
def test_user_not_found() -> None:
    """The command fails if a matching user is not found."""
    stdout = StringIO()
    with pytest.raises(CommandError) as excinfo:
        call_command(THE_COMMAND, "unknown_fxa_id", stdout=stdout)
    assert str(excinfo.value) == "No user with FxA ID 'unknown_fxa_id'."
    assert stdout.getvalue() == ""


def test_dry_run_active_user(phone_user: User) -> None:
    """A dry run reports user data and that there is data to delete."""
    stdout = StringIO()
    call_command(THE_COMMAND, phone_user.profile.fxa.uid, "--dry-run", stdout=stdout)

    expected_stdout = f"""\
Found a matching user:

* FxA ID: decd14f50fce4865b0fd06afcd9d2c4d
* User ID: {phone_user.id}
* Email: phone_user@example.com
* Real Phone: +12005550123
* Relay Phone: +13015550123
* Inbound Contacts: 2

User has phone data to delete.
"""
    assert stdout.getvalue() == expected_stdout

    phone_user.refresh_from_db()
    assert phone_user.profile.has_phone
    assert RealPhone.objects.filter(user=phone_user).exists()
    relay_number = RelayNumber.objects.get(user=phone_user)
    assert InboundContact.objects.filter(relay_number=relay_number).count() == 2


def test_dry_run_no_data(phone_user: User) -> None:
    """A dry run reports user data and that there is no data to delete."""
    RelayNumber.objects.filter(user=phone_user).delete()
    RealPhone.objects.filter(user=phone_user).delete()

    stdout = StringIO()
    call_command(THE_COMMAND, phone_user.profile.fxa.uid, "-n", stdout=stdout)

    expected_stdout = f"""\
Found a matching user:

* FxA ID: decd14f50fce4865b0fd06afcd9d2c4d
* User ID: {phone_user.id}
* Email: phone_user@example.com
* Real Phone: <NO REAL PHONE>
* Relay Phone: <NO RELAY PHONE>
* Inbound Contacts: 0

User has no phone data to delete.
"""
    assert stdout.getvalue() == expected_stdout


@pytest.mark.django_db
def test_dry_run_user_not_found() -> None:
    """The command fails if a matching user is not found."""
    stdout = StringIO()
    with pytest.raises(CommandError) as excinfo:
        call_command(THE_COMMAND, "unknown_fxa_id", "--dry-run", stdout=stdout)
    assert str(excinfo.value) == "No user with FxA ID 'unknown_fxa_id'."
    assert stdout.getvalue() == ""
