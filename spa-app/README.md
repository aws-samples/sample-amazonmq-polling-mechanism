# React SPA Application

## Features

- **Real-time Updates**: Automatically polls DynamoDB every 3 seconds
- **Manual Controls**: Start/stop auto-refresh and manual refresh
- **Add Test Data**: Create sample items directly from the UI
- **Responsive Design**: Clean, modern interface

## Setup

```bash
cd spa-app
npm install
```

## Development

```bash
npm start
```

## Build for Production

```bash
npm run build
```

## Configuration

Update `src/App.js` with your:
- AWS region
- Cognito Identity Pool ID  
- DynamoDB table name

## Deploy to S3

After building, upload the `build/` folder contents to your S3 bucket.

## How It Works

The app automatically fetches changes from DynamoDB using:
- **Polling**: Checks for updates every 3 seconds
- **Real-time UI**: Shows connection status and last update time
- **Interactive**: Add/view items with immediate updates