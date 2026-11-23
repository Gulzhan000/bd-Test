import uuid

from django.db import models


class LoginChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=40)
    code = models.CharField(max_length=5)
    expires_at = models.DateTimeField(db_index=True)
