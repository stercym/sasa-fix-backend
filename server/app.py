#!/usr/bin/env python3
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db
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

    # import models here to register with SQLAlchemy
    from models import User, ServiceProvider, Rating

    # Home URL
    @app.route('/')
    def index():
        return jsonify({"message": "Service Connect API is running!"})

    
    # You can remove this in production. 
    @app.route("/_seed_providers", methods=["POST"])
    def seed_providers():
    
        sample = [
            {"name":"John Mechanic","service_type":"mechanic","location":"Kinoo","phone":"+254712345678"},
            {"name":"Mary Tyre Guy","service_type":"tyre repair","location":"Kasarani","phone":"+254723456789"},
            {"name":"Peter Electrician","service_type":"electrician","location":"Thika","phone":"+254734567890"},
        ]
        created = []
        for s in sample:
            exists = ServiceProvider.query.filter_by(name=s["name"], phone=s["phone"]).first()
            if exists:
                created.append({"name": exists.name, "id": exists.id})
                continue
            p = ServiceProvider(name=s["name"], service_type=s["service_type"], location=s["location"], phone=s["phone"])
            db.session.add(p)
            db.session.flush()
            created.append({"name": p.name, "id": p.id})
        db.session.commit()
        return jsonify({"created": created}), 201

    # AUTHENTICATION
    @app.route("/auth/register", methods=["POST"])
    def auth_register():
        """
        Expects JSON: { name, email, password }
        Creates a new user (no email verification in MVP).
        """
        data = request.get_json() or {}
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "name, email and password are required"}), 400

        if User.query.filter_by(email=email.lower().strip()).first():
            return jsonify({"error": "email already registered"}), 409

        user = User(name=name.strip(), email=email.lower().strip())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "User created successfully", "user": user.to_dict()}), 201

    @app.route("/auth/login", methods=["POST"])
    def auth_login():
        """
        Expects JSON: { email, password }
        Returns: { access_token, user }
        """
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

   
    # SERVICE PROVIDERS
    @app.route("/providers", methods=["GET"])
    def get_providers():
        """
        Query params:
          - service_type (partial match)
          - location (partial match)
        Returns list of providers.
        """
        service_type = request.args.get("service_type", type=str)
        location = request.args.get("location", type=str)

        query = ServiceProvider.query

        if service_type:
            query = query.filter(ServiceProvider.service_type.ilike(f"%{service_type}%"))
        if location:
            query = query.filter(ServiceProvider.location.ilike(f"%{location}%"))

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
        provider = ServiceProvider.query.get_or_404(id)
        return jsonify({
            "id": provider.id,
            "name": provider.name,
            "service_type": provider.service_type,
            "location": provider.location,
            "phone": provider.phone,
            "rating": float(provider.rating or 0.0),
            "reviews": [
                {"id": r.id, "score": r.score, "comment": r.comment, "user_id": r.user_id}
                for r in provider.ratings
            ]
        }), 200

   
    # RATINGS 
    @app.route("/providers/<int:id>/rating", methods=["POST"])
    @jwt_required()
    def rate_provider(id):
        """
        Protected endpoint: logged-in users only.
        Expects JSON: { score: int (1-5), comment: str (optional) }
        Recalculates provider average rating after saving the rating.
        """
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

        provider = ServiceProvider.query.get_or_404(id)

        current_user_id = get_jwt_identity()

        # Prevent duplicate rating by same user for same provider in MVP (optional)
        existing = Rating.query.filter_by(provider_id=provider.id, user_id=current_user_id).first()
        if existing:
            # update existing rating
            existing.score = score
            existing.comment = comment
        else:
            new_rating = Rating(provider_id=provider.id, user_id=current_user_id, score=score, comment=comment)
            db.session.add(new_rating)

        # commit first so relationships are available
        db.session.commit()

        # Recalculate average rating
        ratings = Rating.query.filter_by(provider_id=provider.id).all()
        if ratings:
            avg = sum(r.score for r in ratings) / len(ratings)
        else:
            avg = 0.0
        provider.rating = round(avg, 2)
        db.session.commit()

        return jsonify({"message": "Rating submitted", "rating": provider.rating}), 201


    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
