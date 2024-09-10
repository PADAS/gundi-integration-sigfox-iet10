from datetime import datetime

from .core import GenericJsonTransformConfig, GenericJsonPayload


class BinaryWebhookPayload(GenericJsonPayload):
    device: str
    time: datetime
    data: str
    seqNumber: int
    ack: bool



class BinaryWebhookConfig(GenericJsonTransformConfig):
    pass
