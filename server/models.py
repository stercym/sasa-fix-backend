from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False)  # "client" or "provider"

    # Only providers will have service info
    service_type = db.Column(db.String(120), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)

    # ✅ specify foreign key to remove ambiguity
    ratings_given = db.relationship(
        "Rating",
        foreign_keys="Rating.user_id",
        back_populates="user",
        lazy=True
    )

    ratings_received = db.relationship(
        "Rating",
        foreign_keys="Rating.provider_id",
        back_populates="provider",
        lazy=True
    )

    def set_password(self, password):
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @validates("role")
    def validate_role(self, key, value):
        roles = ["client", "provider"]
        if value not in roles:
            raise ValueError(f"Role must be one of {roles}")
        return value

    @validates("email")
    def validate_email(self, key, value):
        if "@" not in value:
            raise ValueError("Invalid email format")
        return value

    @validates("phone")
    def validate_phone(self, key, value):
        if self.role == "provider" and (value is None or len(value.strip()) < 9):
            raise ValueError("Service providers must have a valid phone number")
        return value

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }

        if self.role == "provider":
            data.update({
                "service_type": self.service_type,
                "location": self.location,
                "phone": self.phone,
                "rating": self.rating,
                "reviews": [review.to_dict() for review in self.ratings_received]
            })

        return data

    @property
    def rating(self):
        if len(self.ratings_received) == 0:
            return 0
        total = sum([r.score for r in self.ratings_received])
        return round(total / len(self.ratings_received), 1)


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)

    provider_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)

    # ✅ explicit relationship definitions
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="ratings_given"
    )

    provider = db.relationship(
        "User",
        foreign_keys=[provider_id],
        back_populates="ratings_received"
    )

    @validates("score")
    def validate_score(self, key, value):
        if value < 1 or value > 5:
            raise ValueError("Rating must be between 1 and 5")
        return value

    def to_dict(self):
        return {
            "id": self.id,
            "score": self.score,
            "comment": self.comment,
            "provider_id": self.provider_id,
            "user_id": self.user_id,
            "user": self.user.name if self.user else None
        }
