from pydantic import BaseModel


class Message(BaseModel):
    receiver_id: str
    message_txt: str
