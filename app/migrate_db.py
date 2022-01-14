from app import app, db
from models import User, NFT

app.app_context().push()
db.create_all()
