import os
import argparse
from dotenv import load_dotenv
from livekit import api

load_dotenv()

def generate_token(room_name: str, identity: str = "playground_user"):
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret or not livekit_url:
        print("Error: LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL must be set in .env")
        return

    token = api.AccessToken(api_key, api_secret) \
        .with_identity(identity) \
        .with_name(identity) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        ))

    jwt_token = token.to_jwt()

    print(f"\n--- LiveKit Playground Token ---")
    print(f"Room: {room_name}")
    print(f"Identity: {identity}")
    print(f"\nToken:\n{jwt_token}\n")

    # Construct Playground URL
    # Assuming the standard hosted playground.
    # The URL structure is usually https://agents-playground.livekit.io/#<token>
    # or it might just take the token in the settings.
    # Actually, the playground usually takes params via UI, but having the token is the main step.

    print(f"--- Instructions ---")
    print(f"1. Go to https://agents-playground.livekit.io/")
    print(f"2. Click 'Settings' (gear icon) or 'Connect'.")
    print(f"3. URL: {livekit_url}")
    print(f"4. Paste the Token above.")
    print(f"5. Connect.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a LiveKit token for the Agents Playground.")
    parser.add_argument("--room", type=str, default="playground-test", help="The room name to join.")
    parser.add_argument("--identity", type=str, default="playground_user", help="The user identity.")

    args = parser.parse_args()
    generate_token(args.room, args.identity)
