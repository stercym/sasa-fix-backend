from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Relationship: A user can create many ratings/reviews
    ratings = db.relationship("Rating", backref="user", lazy=True)

    def set_password(self, password):
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email
        }


class ServiceProvider(db.Model):
    __tablename__ = "service_providers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    service_type = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)

    ratings = db.relationship("Rating", backref="provider", lazy=True)

    # Validation: ensure certain service types only
    __table_args__ = (
        db.CheckConstraint("length(name) > 0", name="provider_name_not_empty"),
        db.CheckConstraint("length(service_type) > 0", name="provider_service_not_empty"),
        db.CheckConstraint("length(phone) > 0", name="provider_phone_not_empty"),
    )

    @property
    def rating(self):
        """Compute average rating from Rating table."""
        if not self.ratings or len(self.ratings) == 0:
            return 0
        total = sum([r.score for r in self.ratings])
        return round(total / len(self.ratings), 1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type,
            "location": self.location,
            "phone": self.phone,
            "rating": self.rating,
            "reviews": [review.to_dict() for review in self.ratings]
        }


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("service_providers.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # Optional: track who rated
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)

    __table_args__ = (
        db.CheckConstraint("score >= 1 AND score <= 5", name="valid_rating_range"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "score": self.score,
            "comment": self.comment,
            "provider_id": self.provider_id,
            "user_id": self.user_id,
            "user": self.user.name if self.user else None
        }
