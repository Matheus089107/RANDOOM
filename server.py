import os
import json
import asyncio
import mimetypes
from aiohttp import web

# Previne o aiohttp de adicionar Content-Encoding: gzip nos arquivos do Pygbag
# Isso evita que o navegador descompacte os arquivos antes da engine do jogo.
if '.gz' in mimetypes.encodings_map:
    del mimetypes.encodings_map['.gz']

# Dicionários de estado global
rooms = {}
player_data = {}

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    room_id = None
    p_id = "???"
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                
                if data["type"] == "join":
                    room_id = data["room"]
                    p_id = data.get("id", "??")
                    player_data[ws] = p_id
                    
                    if room_id not in rooms:
                        rooms[room_id] = []
                    
                    print(f"--- [JOIN] Jogador {p_id} pedindo entrada na sala {room_id} ---")
                    
                    # Sincronização de IDs: Todo mundo se conhece
                    for client in rooms[room_id]:
                        veteran_id = player_data.get(client, "??")
                        # Veterano avisa o novato que ele existe
                        await ws.send_json({"type": "player_joined", "id": veteran_id})
                        # Novato avisa o veterano que ele chegou
                        await client.send_json({"type": "player_joined", "id": p_id})
                        print(f"Sincronizando: {p_id} <-> {veteran_id}")
                        
                    rooms[room_id].append(ws)
                    print(f"Sala {room_id} agora tem {len(rooms[room_id])} jogadores.")

                # Repassa QUALQUER mensagem da sala para os outros jogadores
                elif room_id and room_id in rooms:
                    message_to_send = msg.data # Pode mandar a string pura direto
                    for client in rooms[room_id]:
                        if client != ws:
                            await client.send_str(message_to_send)
                            
            elif msg.type == web.WSMsgType.ERROR:
                print(f'Conexão com o {p_id} teve um erro: {ws.exception()}')
                
    except Exception as e:
        print(f"Erro na conexão com {p_id}: {e}")
    finally:
        # Remover o jogador da sala ao desconectar
        if room_id in rooms and ws in rooms[room_id]:
            rooms[room_id].remove(ws)
            print(f"--- [LEAVE] Jogador {p_id} saiu da sala {room_id} ---")
            
            # Avisar os outros que este jogador saiu
            for client in rooms[room_id]:
                try:
                    await client.send_json({"type": "player_left", "id": p_id})
                except Exception:
                    pass
                
            if not rooms[room_id]:
                del rooms[room_id]
                print(f"Sala {room_id} encerrada.")
        else:
            print(f"Conexão perdida com {p_id} (sem sala)")

    return ws

async def index_handler(request):
    path = os.path.join(os.getcwd(), 'build', 'web', 'index.html')
    if os.path.exists(path):
        return web.FileResponse(path)
    return web.Response(text="Erro: build/web/index.html não encontrado no servidor!", status=404)

@web.middleware
async def add_coop_coep_headers(request, handler):
    response = await handler(request)
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'credentialless'
    return response

async def init_app():
    app = web.Application(middlewares=[add_coop_coep_headers])
    
    # 1. Rota WebSocket
    app.router.add_get('/ws', websocket_handler)
    
    # 2. Rota Frontend Principal
    app.router.add_get('/', index_handler)
    
    # 3. Servir arquivos criados pelo Pygbag em build/web
    base_dir = os.getcwd()
    build_dir = os.path.join(base_dir, 'build', 'web')
    
    print(f"DEBUG: Verificando diretório de build em: {build_dir}")
    if os.path.exists(build_dir):
        print(f"DEBUG: Diretório encontrado! Servindo arquivos estáticos de {build_dir}")
        # Usamos show_index=False por segurança
        app.router.add_static('/', build_dir, show_index=False)
    else:
        print(f"ERROR: Diretório {build_dir} NÃO ENCONTRADO! O jogo não vai carregar.")
        
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Iniciando Servidor na porta {port}...")
    print(f"Pasta Atual (CWD): {os.getcwd()}")
    web.run_app(init_app(), port=port)
