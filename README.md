To start the back end fromproject root:
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8012

## Android Setup

1. Install Android Studio
2. Install Android SDK
3. Create `android/local.properties` with:

sdk.dir=/Users/YOUR_USERNAME/Library/Android/sdk

4. Run:

npx react-native run-android
