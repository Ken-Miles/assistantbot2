from typing import Optional

class UsedPrefixCommandException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __str__(self, command_mention: str="the slash version of this command"):
        return f"This command can only be used as a slash command. Try using {command_mention} instead."

async def setup(*args):
    pass