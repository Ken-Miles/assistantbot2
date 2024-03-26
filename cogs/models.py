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


class Cases(Base):
    user_id = fields.BigIntField()
    moderator_id = fields.BigIntField()
    
    guild_id = fields.BigIntField()
    """Should be 0 if it was a global action"""
    case_id = fields.IntField()
    """Case number per guild."""

    performed_with_bot = fields.BooleanField(default=False)
    annonymous = fields.BooleanField(default=False)
    """Whether the moderator should be shown when the case is looked up."""

    action = fields.CharField(max_length=50)
    reason = fields.TextField(null=True)

    sucessful = fields.BooleanField(default=True)
    """Whether the action was sucessful or not."""
    
    active = fields.BooleanField(default=True)

    class Meta:
        table = "Cases"
    
    @staticmethod
    async def get_next_case_num(guild_id: int) -> int:
        """Gets the next case number for a guild.

        Args:
            guild_id (int): ID of the guild.

        Returns:
            int: Next case number.
        """        
        assert guild_id, "guild_id is required"
        last_case = await Cases.filter(guild_id=guild_id).order_by('-case_id').first()
        if last_case:
            return last_case.case_id + 1
        return 1

    @staticmethod
    async def get_next_id():
        """Gets the next global ID.

        Returns:
            int: Next global ID.
        """        
        last_case = await Cases.all().order_by('-id').first()
        if last_case:
            return last_case.id + 1
        return 1

class BotBans(Base):
    user_id = fields.BigIntField()
    moderator_id = fields.BigIntField()
    reason = fields.TextField(null=True)
    active = fields.BooleanField(default=True)

    class Meta:
        table = "BotBans"

async def setup(*args):
    await Tortoise.init(config_file='db.yml')
    await Tortoise.generate_schemas()
