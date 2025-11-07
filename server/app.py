#!/usr/bin/env python3
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, User, Rating
from config import Config
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", timedelta(days=7))

    CORS(app, supports_credentials=True)
    db.init_app(app)
    jwt = JWTManager()
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Home URL
    @app.route('/')
    def index():
        return jsonify({"message": "Service Connect API is running!"})


    # DEVELOPMENT ONLY: Seed sample providers
    @app.route("/_seed_providers", methods=["POST"])
    def seed_providers():

        sample = [
            {"name":"John Mechanic","service_type":"mechanic","location":"Kinoo","phone":"+254712345678"},
            {"name":"Mary Tyre Guy","service_type":"tyre repair","location":"Kasarani","phone":"+254723456789"},
            {"name":"Peter Electrician","service_type":"electrician","location":"Thika","phone":"+254734567890"},
        ]
        created = []
        for s in sample:
            exists = User.query.filter_by(name=s["name"], phone=s["phone"], role="provider").first()
            if exists:
                created.append({"name": exists.name, "id": exists.id})
                continue

            p = User(
                name=s["name"],
                email=f"{s['name'].replace(' ', '').lower()}@example.com",
                role="provider",
                service_type=s["service_type"],
                location=s["location"],
                phone=s["phone"]
            )

            p.set_password("password")  # Default password for seed only
            db.session.add(p)
            db.session.flush()

            created.append({"name": p.name, "id": p.id})

        db.session.commit()
        return jsonify({"created": created}), 201


    # AUTHENTICATION
    @app.route("/auth/register", methods=["POST"])
    def auth_register():
        data = request.get_json() or {}
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role", "client")

        if not name or not email or not password:
            return jsonify({"error": "name, email and password are required"}), 400

        if role not in ["client", "provider"]:
            return jsonify({"error": "role must be either 'client' or 'provider'"}), 400

        if User.query.filter_by(email=email.lower().strip()).first():
            return jsonify({"error": "email already registered"}), 409

        user = User(
            name=name.strip(),
            email=email.lower().strip(),
            role=role,
            service_type=data.get("service_type"),
            location=data.get("location"),
            phone=data.get("phone")
        )

        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "User created successfully", "user": user.to_dict()}), 201


    @app.route("/auth/login", methods=["POST"])
    def auth_login():
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "invalid credentials"}), 401

        access_token = create_access_token(identity=user.id)
        return jsonify({"access_token": access_token, "user": user.to_dict()}), 200


    @app.route("/users/me", methods=["GET"])
    @jwt_required()
    def users_me():
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        return jsonify(user.to_dict()), 200


    # SERVICE PROVIDERS (from User table where role = provider)
    @app.route("/providers", methods=["GET"])
    def get_providers():
        service_type = request.args.get("service_type", type=str)
        location = request.args.get("location", type=str)

        query = User.query.filter_by(role="provider")

        if service_type:
            query = query.filter(User.service_type.ilike(f"%{service_type}%"))
        if location:
            query = query.filter(User.location.ilike(f"%{location}%"))

        providers = query.all()

        return jsonify([
            {
                "id": p.id,
                "name": p.name,
                "service_type": p.service_type,
                "location": p.location,
                "phone": p.phone,
                "rating": float(p.rating or 0.0),
            }
            for p in providers
        ]), 200


    @app.route("/providers/<int:id>", methods=["GET"])
    def get_provider(id):
        provider = User.query.filter_by(id=id, role="provider").first_or_404()
        return jsonify(provider.to_dict()), 200


    # RATINGS
    @app.route("/providers/<int:id>/rating", methods=["POST"])
    @jwt_required()
    def rate_provider(id):
        data = request.get_json() or {}
        score = data.get("score")
        comment = data.get("comment", "")

        if score is None:
            return jsonify({"error": "score is required (1-5)"}), 400

        try:
            score = int(score)
        except (TypeError, ValueError):
            return jsonify({"error": "score must be an integer between 1 and 5"}), 400

        if score < 1 or score > 5:
            return jsonify({"error": "score must be between 1 and 5"}), 400

        provider = User.query.filter_by(id=id, role="provider").first_or_404()

        current_user_id = get_jwt_identity()

        existing = Rating.query.filter_by(provider_id=provider.id, user_id=current_user_id).first()
        if existing:
            existing.score = score
            existing.comment = comment
        else:
            new_rating = Rating(provider_id=provider.id, user_id=current_user_id, score=score, comment=comment)
            db.session.add(new_rating)

        db.session.commit()

        return jsonify({"message": "Rating submitted"}), 201


    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
