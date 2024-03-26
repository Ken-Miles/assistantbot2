import tortoise
from tortoise import Tortoise, fields, models

class Base(models.Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

class MinecraftLinkedUsers(Base):
    discord_id = fields.BigIntField()
    minecraft_uuid = fields.UUIDField(null=True)
    minecraft_username = fields.CharField(max_length=16)
    isjava = fields.BooleanField()
    linked_by = fields.BigIntField()

    @property
    def is_bedrock(self):
        return not self.isjava

    class Meta:
        table = "MinecraftLinkedUsers"

async def setup(*args):
    await Tortoise.init(config_file='db.yml')
    await Tortoise.generate_schemas()
