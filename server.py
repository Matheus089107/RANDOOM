import asyncio
import sys
import subprocess
import json

try:
    import websockets
except ImportError:
    print("Fazendo o download automático do websockets no servidor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets==12.0"])
    import websockets


# Dicionários de estado global
rooms = {}
player_data = {}

async def handler(websocket):
    room_id = None
    p_id = "???"
    try:
        async for message in websocket:
            data = json.loads(message)
            
            if data["type"] == "join":
                room_id = data["room"]
                p_id = data.get("id", "??")
                player_data[websocket] = p_id
                
                if room_id not in rooms:
                    rooms[room_id] = []
                
                print(f"--- [JOIN] Jogador {p_id} pedindo entrada na sala {room_id} ---")
                
                # Sincronização de IDs: Todo mundo se conhece
                for client in rooms[room_id]:
                    veteran_id = player_data.get(client, "??")
                    # Veterano avisa o novato que ele existe
                    await websocket.send(json.dumps({"type": "player_joined", "id": veteran_id}))
                    # Novato avisa o veterano que ele chegou
                    await client.send(json.dumps({"type": "player_joined", "id": p_id}))
                    print(f"Sincronizando: {p_id} <-> {veteran_id}")
                    
                rooms[room_id].append(websocket)
                print(f"Sala {room_id} agora tem {len(rooms[room_id])} jogadores.")

            # Repassa QUALQUER mensagem da sala para os outros jogadores
            elif room_id:
                if room_id in rooms:
                    message_to_send = json.dumps(data)
                    for client in rooms[room_id]:
                        if client != websocket:
                            await client.send(message_to_send)
    except Exception as e:
        print(f"Erro na conexão com {p_id}: {e}")
    finally:
        # Remover o jogador da sala ao desconectar
        if room_id in rooms and websocket in rooms[room_id]:
            rooms[room_id].remove(websocket)
            print(f"--- [LEAVE] Jogador {p_id} saiu da sala {room_id} ---")
            
            # Avisar os outros que este jogador saiu
            for client in rooms[room_id]:
                try:
                    await client.send(json.dumps({"type": "player_left", "id": p_id}))
                except: pass
                
            if not rooms[room_id]:
                del rooms[room_id]
                print(f"Sala {room_id} encerrada.")
        else:
            print(f"Conexão perdida com {p_id} (sem sala)")

async def main():
    import os
    port = int(os.environ.get("PORT", 8080))
    print(f"Servidor de Doom Multiplayer Iniciando...")
    # origins=None permite conexões de qualquer domínio (importante para Vercel)
    async with websockets.serve(handler, "0.0.0.0", port, origins=None):
        print(f"Ouvindo na porta {port}...")
        await asyncio.Future()  # roda para sempre

if __name__ == "__main__":
    asyncio.run(main())
