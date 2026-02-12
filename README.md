<div align="center">

  <img src="frontend/public/vite.svg" alt="logo" width="100" height="auto" />
  <h1>CyptoQuant Analytics</h1>
  
  <p>
    An advanced cryptocurrency price forecasting tool powered by LSTM neural networks.
  </p>
  
  
<!-- Badges -->
<p>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/graphs/contributors">
    <img src="https://img.shields.io/github/contributors/AaravKashyap12/CryptoQuant" alt="contributors" />
  </a>
  <a href="">
    <img src="https://img.shields.io/github/last-commit/AaravKashyap12/CryptoQuant" alt="last update" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/network/members">
    <img src="https://img.shields.io/github/forks/AaravKashyap12/CryptoQuant" alt="forks" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/stargazers">
    <img src="https://img.shields.io/github/stars/AaravKashyap12/CryptoQuant" alt="stars" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/issues/">
    <img src="https://img.shields.io/github/issues/AaravKashyap12/CryptoQuant" alt="open issues" />
  </a>
  <a href="https://github.com/AaravKashyap12/CryptoQuant/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/AaravKashyap12/CryptoQuant.svg" alt="license" />
  </a>
</p>
   
<h4>
    <a href="https://github.com/AaravKashyap12/CryptoQuant/">View Demo</a>
  <span> · </span>
    <a href="https://github.com/AaravKashyap12/CryptoQuant">Documentation</a>
  <span> · </span>
    <a href="https://github.com/AaravKashyap12/CryptoQuant/issues/">Report Bug</a>
  <span> · </span>
    <a href="https://github.com/AaravKashyap12/CryptoQuant/issues/">Request Feature</a>
  </h4>
</div>

<br />

<!-- Table of Contents -->
# :notebook_with_decorative_cover: Table of Contents

- [About the Project](#star2-about-the-project)
  - [Screenshots](#camera-screenshots)
  - [Tech Stack](#space_invader-tech-stack)
  - [Features](#dart-features)
- [Getting Started](#toolbox-getting-started)
  - [Prerequisites](#bangbang-prerequisites)
  - [Installation](#gear-installation)
  - [Run Locally](#running-run-locally)
- [Usage](#eyes-usage)
- [Roadmap](#compass-roadmap)
- [Contributing](#wave-contributing)
- [License](#warning-license)
- [Contact](#handshake-contact)

<!-- About the Project -->
## :star2: About the Project

**CryptoQuant** is a sophisticated forecasting dashboard designed to analyze cryptocurrency market trends using deep learning. By leveraging historical OHLCV data from Binance, our LSTM model identifies complex patterns and projects future price movements with dynamic confidence intervals.

<!-- Screenshots -->
### :camera: Screenshots

<div align="center"> 
  <img src="https://placehold.co/800x400?text=Dashboard+Screenshot+Here" alt="screenshot" />
</div>

<!-- TechStack -->
### :space_invader: Tech Stack

<details>
  <summary>Client</summary>
  <ul>
    <li><a href="https://reactjs.org/">React.js</a></li>
    <li><a href="https://tailwindcss.com/">TailwindCSS</a></li>
    <li><a href="https://www.framer.com/motion/">Framer Motion</a></li>
    <li><a href="https://recharts.org/">Recharts</a></li>
  </ul>
</details>

<details>
  <summary>Server</summary>
  <ul>
    <li><a href="https://fastapi.tiangolo.com/">FastAPI</a></li>
    <li><a href="https://www.tensorflow.org/">TensorFlow/Keras</a></li>
    <li><a href="https://pandas.pydata.org/">Pandas & NumPy</a></li>
    <li><a href="https://scikit-learn.org/">Scikit-learn</a></li>
    <li><a href="https://www.docker.com/">Docker</a></li>
  </ul>
</details>

<!-- Features -->
### :dart: Features

- **Store Data**: Fetch real-time and historical data from Binance API.
- **Analyze Trends**: Calculate key technical indicators (RSI, MACD, Volatility).
- **Predict Prices**: forecast future prices using LSTM neural networks.
- **Visualize**: Interactive charts with zoomable timeframes and confidence bands.
- **Explainability**: "White-box" model insights explaining why a prediction was made.
- **Auto-Pilot**: Continuous background retraining every 24 hours to ensure fresh models.

<!-- Getting Started -->
## :toolbox: Getting Started

Follow these steps to set up the project locally.

<!-- Prerequisites -->
### :bangbang: Prerequisites

This project uses Python for the backend and Node.js for the frontend.

- **Node.js**: v18+
- **Python**: v3.9+
- **Pip**: Latest version

<!-- Installation -->
### :gear: Installation

1. Clone the repo
   ```bash
   git clone https://github.com/AaravKashyap12/CryptoQuant.git
   ```
2. Navigate to project directory
   ```bash
   cd CryptoQuant
   ```

<!-- Run Locally -->
### :running: Run Locally
    
#### Quick Start (Recommended)

Double-click `run_app.bat` to launch both the Backend and Frontend automatically.

#### Manual Startup

**Backend (Python/FastAPI)**
1. Go to `backend/`
2. Activate venv: `..\.venv\Scripts\activate`
3. Run: `uvicorn main:app --reload --port 8001`

**Frontend (React/Vite)**
1. Go to `frontend/`
2. Run: `npm run dev`

### :brain: Model Retraining

To update the models with the latest real market data:

1. Ensure the app is running (`run_app.bat`).
2. Run the training script:
   ```bash
   python scripts/train_models.py
   ```
3. This will trigger a background job. Models update in ~5-10 minutes.

Open `http://localhost:5173` in your browser.

<!-- Deployment -->
## :rocket: Deployment

### Deploy on Render (Recommended)

1.  Push your code to GitHub.
2.  Go to [Render Dashboard](https://dashboard.render.com/).
3.  Click **New +** -> **Web Service**.
4.  Connect your GitHub repository.
5.  Render will automatically detect `render.yaml` and configure the deployment.
6.  Click **Create Web Service**.

That's it! Your API will be live in minutes.

### Deploy Frontend on Vercel

1.  Push your code to GitHub.
2.  Go to [Vercel Dashboard](https://vercel.com/dashboard).
3.  Click **Add New...** -> **Project**.
4.  Import the `CryptoQuant` repository.
5.  **Configure Project**:
    - **Framework Preset**: Vite
    - **Root Directory**: `frontend` (Click Edit)
    - **Environment Variables**:
      - `VITE_API_URL`: `https://your-render-backend-url.onrender.com` (Get this from Render)
6.  Click **Deploy**.

Your frontend will be live and connected to your backend! 🚀

<!-- Usage -->
## :eyes: Usage

- **Select a Coin**: Use the dropdown (e.g., BTC, ETH) to switch assets.
- **View Forecast**: Check the yellow dashed line for the 7-day price prediction.
- **Analyze Metrics**: Review the cards for daily change, predicted ROI, and volatility risk.
- **Validate**: Scroll down to see how accurate the model has been over the last 30 days.

<!-- Roadmap -->
## :compass: Roadmap

* [x] Core LSTM Model Implementation
* [x] Real-time Binance Integration
* [x] Interactive Price Charts
* [x] Model Explainability Modal
* [ ] Multi-Model Ensemble (XGBoost + LSTM)
* [ ] Sentiment Analysis Integration (Twitter/Reddit)
* [ ] User Authentication & Portfolio Tracking

<!-- Contributing -->
## :wave: Contributing

Contributions are always welcome!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<!-- License -->
## :warning: License

Distributed under the MIT License. See `LICENSE` for more information.

<!-- Contact -->
## :handshake: Contact

Aarav Kashyap - [@KashyapAarav_](https://x.com/KashyapAarav_)

Project Link: [https://github.com/AaravKashyap12/CryptoQuant](https://github.com/AaravKashyap12/CryptoQuant)
