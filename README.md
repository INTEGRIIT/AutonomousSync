Aamazon EC2 setup
sudo apt update
sudo apt install git python3-pip -y


Amazon AWS EC2 instance
# SSH into instance
ssh -i ~/.ssh/AutonomousSynckey.pem ubuntu@3.80.27.210

# Update system
sudo apt update && sudo apt upgrade -y

# Clone repository
git clone <repo_url>
cd backend

# Install dependencies
pip3 install -r requirements.txt

# Run backend
uvicorn app:app --host 0.0.0.0 --port 8012





To start the back end fromproject root:
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8012

## Android Setup

1. Install Android Studio
2. Install Android SDK
3. Create `android/local.properties` with:

sdk.dir=/Users/YOUR_USERNAME/Library/Android/sdk

4. Run:

npx react-native run-android





cd android
./gradlew clean
cd ..
npx expo run:android




cd ios
pod repo update
pod install
cd ..




python log_listener.py
python log_listener.py live

python log_listener.py full


python log_listener.py full 500
?mode=full&limit=500