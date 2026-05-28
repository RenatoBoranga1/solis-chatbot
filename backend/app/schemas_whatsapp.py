from pydantic import BaseModel, Field


class WhatsAppIncomingMessage(BaseModel):
    wa_id: str
    phone: str
    contact_name: str | None = None
    message_id: str
    text: str
    timestamp: str | None = None
    message_type: str
    media_id: str | None = None
    attachment_url: str | None = None
    raw_type_payload: dict = Field(default_factory=dict)


class WhatsAppWebhookResult(BaseModel):
    status: str
    processed: int = 0
    duplicates: int = 0
    ignored: int = 0
