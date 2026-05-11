from sqlmodel import SQLModel, Field, Relationship, select
from typing import List
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}# Utilisation d'une classe pour mettre en place la méthode websocket

    async def broadcast_user_list(self):
        active_users = list(self.active_connections.keys())
        message = {
            "type": "USER_LIST",
            "data": active_users
        }
        for connection in self.active_connections.values():
            await connection.send_json(message)
#les fonctions qui suivent permettent une mise à jour régulière de la page en fonction des actions de l'utilisateur 
    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        await self.broadcast_user_list()

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            await self.broadcast_user_list()

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

class User(SQLModel, table = True): #mise en place des relations entre les differentes classes : User et Message
    id : int | None = Field(default=None, primary_key=True)
    name : str
    email : str = Field(unique = True)

    messages_envoyes : List["Message"] = Relationship(back_populates="user_exp",
                                                      sa_relationship_kwargs={"foreign_keys": "Message.exp_id"})
    messages_recus : List["Message"] = Relationship(back_populates="user_dest",
                                                    sa_relationship_kwargs={"foreign_keys": "Message.dest_id"})

class Message(SQLModel, table = True):
    id_mess : int | None = Field(default=None, primary_key=True)
    user_exp : User = Relationship(back_populates='messages_envoyes',
                                   sa_relationship_kwargs={"foreign_keys": "Message.exp_id"})
    exp_id : int = Field(foreign_key="user.id")
    user_dest : User =Relationship(back_populates='messages_recus',
                                   sa_relationship_kwargs={"foreign_keys": "Message.dest_id"})
    dest_id : int = Field(foreign_key="user.id") 
    mess_content : str
    mess_date : int = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mess_status : str = Field(default='non_lu')


from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import create_engine, Session
database_url = "sqlite:///./main.db"
engine = create_engine(database_url, echo=True)

# create tables
# of course this needs to come AFTER all model definitions...
SQLModel.metadata.create_all(engine)

# utility function to get a session
def get_session():
    with Session(engine) as session:
        yield session
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # L'étoile signifie "J'autorise tout le monde" (pratique en dev)
    allow_credentials=True,
    allow_methods=["*"], # Autorise toutes les méthodes (GET, POST, PATCH, DELETE)
    allow_headers=["*"], # Autorise tous les en-têtes
)

def messages_non_lus(liste_message : List[Message]):
    Liste = []
    for message in liste_message:
        if message.mess_status == 'non_lu':
            Liste.append(message)
    return Liste

#mise en place de la méthode websocket pour permettre une actualisation en live de la messagerie 
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text() # Maintient de la connexion ouverte
    except WebSocketDisconnect:
        await manager.disconnect(user_id)

@app.post("/users/", response_model = User)
def create_user(user : User, session: Session = Depends(get_session) ):
    session.add(user)
    session.commit()
    session.refresh(user)  
    return user

@app.get("/users/", response_model=List[User])
def list_users(session: Session = Depends(get_session)):
    users = session.exec(select(User)).all()
    return users

@app.get("/users/{user_id}", response_model = User)
def get_user1(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    return user

@app.post("/messages/", response_model=Message)
async def create_message(message: Message, session: Session = Depends(get_session)):
    session.add(message)
    session.commit()
    session.refresh(message)
    await manager.send_personal_message({
        "type": "NEW_MESSAGE",
        "data": {
            "id_mess": message.id_mess,
            "exp_id": message.exp_id,
            "mess_content": message.mess_content
        }
    }, message.dest_id)
    
    return message

@app.get("/users/{user_id}/inbox", response_model = List[Message])
def get_messages_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    return messages_non_lus(user.messages_recus)

@app.get("/users/{user_id}/sent", response_model = List[Message])
def get_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    return user.messages_envoyes

@app.get("/messages/{message_id}", response_model = str)
def get_message_content(message_id: int, session: Session = Depends(get_session)):
    message = session.get(Message, message_id)
    return message.mess_content

@app.patch("/messages/{message_id}/read", response_model = Message)
def get_user2(message_id: int, session: Session = Depends(get_session)):
    message = session.get(Message, message_id)
    new_status = 'lu'
    message.mess_status = new_status
    session.add(message)
    session.commit()
    session.refresh(message)  
    return message

@app.delete("/messages/{message_id}")
def delete_message(message_id :int, session:Session = Depends(get_session)):
    message = session.get(Message, message_id)
    session.delete(message)
    session.commit()








