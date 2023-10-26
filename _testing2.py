import asyncio
import asqlite

async def main():
    async with asqlite.connect('users.db') as conn:
        async with conn.cursor() as cursor:
            allplayers = []
            await cursor.execute('SELECT * FROM Players')
            users = []
            for row in await cursor.fetchall():
                row = dict(row)
                if row.get('mcusername') not in users: 
                    allplayers.append(row)
                    users.append(row.get('mcusername'))
            
            await cursor.execute('CREATE TABLE IF NOT EXISTS NewPlayers(dbid INTEGER PRIMARY KEY AUTOINCREMENT, datelogged INTEGER, lastupdated INTEGER, mcusername TEXT, mcuuid TEXT, UNIQUE(mcusername, mcuuid, dbid)) STRICT')

            for player in allplayers:
                await cursor.execute('INSERT INTO NewPlayers (datelogged, lastupdated, mcusername, mcuuid) VALUES (?,?,?,?)', (player.get('datelogged'), player.get('lastupdated'), player.get('mcusername'), player.get('mcuuid')))
            await conn.commit()
# import requests

# s = requests.Session()

# s.headers.update({
#     "Authorization": "Bot NTE0MTUzNTUyNzg5MzcyOTI5.GjnFpS.dG-N0XsDr4Qwwwj4UqtDmzmDOkZTZgAP2z45YA",
#     "X-Super-Properties": "eyJvcyI6IkxpbnV4IiwiYnJvd3NlciI6IkZpcmVmb3giLCJkZXZpY2UiOiIiLCJzeXN0ZW1fbG9jYWxlIjoicnUtUlUiLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoWDExOyBMaW51eCB4ODZfNjQ7IHJ2OjEwOS4wKSBHZWNrby8yMDEwMDEwMSBGaXJlZm94LzExNy4wIiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE3LjAiLCJvc192ZXJzaW9uIjoiIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjIyNzEwMiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0="
# })

# url = 'https://discord.com/api/v9/channels/1029151630676987929/voice-status'

# params = {"status": "e"}

# resp = s.put(url, json=params)
# print(resp.status_code)

#if __name__ == "__main__": asyncio.run(main())