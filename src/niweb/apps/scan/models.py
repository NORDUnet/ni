from django.db import models

# Create your models here.

QUEUE_TYPES = [
    ("Host", "Host"),
]

STATUS = [
    ("QUEUED", "Queued"),
    ("PROCESSING", "Processing"),
    ("DONE", "Done"),
    ("FAILED", "Failed"),
]


class QueueItem(models.Model):
    type =  models.CharField(max_length=255, choices=QUEUE_TYPES)
    status = models.CharField(max_length=255, choices=STATUS, default="QUEUED")
    data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return "{0} ({1})".format(self.type, self.status)
