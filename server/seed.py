from app import app
from models import db, User, Rating

with app.app_context():

    print("Dropping existing tables...")
    db.drop_all()

    print("Creating new tables...")
    db.create_all()

    print("Seeding Users (Clients)...")

    user1 = User(name="Alice Johnson", email="alice@example.com", role="client")
    user1.set_password("alice123")

    user2 = User(name="Brian Kim", email="brian@example.com", role="client")
    user2.set_password("brian123")

    user3 = User(name="Chanel Amani", email="chanel@example.com", role="client")
    user3.set_password("chanel123")

    print("Seeding Users (Service Providers)...")

    provider1 = User(
        name="FixIt Plumbing Co.",
        email="fixit@example.com",
        role="provider",
        service_type="Plumbing",
        location="Nairobi",
        phone="0700123456"
    )
    provider1.set_password("fixit123")

    provider2 = User(
        name="Spark Electricals",
        email="spark@example.com",
        role="provider",
        service_type="Electrical",
        location="Thika",
        phone="0712345678"
    )
    provider2.set_password("spark123")

    provider3 = User(
        name="CleanSweep Services",
        email="cleansweep@example.com",
        role="provider",
        service_type="Cleaning",
        location="Westlands",
        phone="0798765432"
    )
    provider3.set_password("clean123")

    db.session.add_all([user1, user2, user3, provider1, provider2, provider3])
    db.session.commit()

    print("Seeding Ratings...")

    rating1 = Rating(
        score=5,
        comment="They fixed my sink very fast! Highly recommended.",
        provider_id=provider1.id,
        user_id=user1.id
    )

    rating2 = Rating(
        score=4,
        comment="Good service but was slightly late.",
        provider_id=provider1.id,
        user_id=user2.id
    )

    rating3 = Rating(
        score=3,
        comment="Affordable but could improve on communication.",
        provider_id=provider3.id,
        user_id=user3.id
    )

    db.session.add_all([rating1, rating2, rating3])
    db.session.commit()

    print("✅ Database seeding completed successfully!")
