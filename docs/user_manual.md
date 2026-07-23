# User Manual

## 1. Choosing your language

When you open HealTheCrop, the name of a language appears at the top of the screen and
changes every few seconds — English, then Hindi, Kannada, Tamil, Telugu, Malayalam, on
repeat. This is there so you can find the language switch even if you can't read any of the
languages listed yet. Tap any language name (in the row of buttons below the animation, or
the compact dropdown in the top bar on any page) to switch the whole app to that language
instantly — menus, buttons, forms, and results all change together.

## 2. Creating an account

Tap **Create Your Account** on the home page. Enter your name, email, a password (at least
6 characters), and optionally your location and phone number. Location helps the crop
recommendation model account for regional growing conditions.

## 3. Dashboard

After logging in, the **Dashboard** shows:
- Live values from any connected ESP32 sensor node (soil moisture, temperature, humidity,
  pH, nitrogen) with a color-coded status dot: green = excellent/good, yellow = average,
  orange/red = poor/critical.
- A **Fertility Score** out of 100.
- Historical trend charts for the last 30 readings.
- Storage and connection status.

If no device is connected yet, use **Manual Input** instead.

## 4. Manual Input (no hardware required)

Go to **Manual Input**, enter your soil's nitrogen, phosphorus, potassium, temperature,
humidity, pH, and rainfall values (defaults are pre-filled for a quick demo), optionally pick
a season or leave it on auto-detect, and tap **Get Crop Recommendation**.

You'll see a row of crop cards — the top recommendation is highlighted, followed by four
alternatives. Each card shows a picture, the crop's name, a confidence percentage, the
suitable season, water requirement, harvest duration, soil suitability, and expected yield —
so you can recognize a suitable crop even without reading its name.

## 5. Scan Crop (pest & disease detection)

Go to **Scan Crop**, tap **Upload Image**, and choose a clear photo of a leaf, fruit, stem,
or whole plant (JPEG/PNG/WEBP, under 10MB). Tap **Submit**. Within a few seconds you'll see:
- The detected disease or pest name and a confidence score.
- A description of what it looks like.
- **Organic treatment** and **Chemical treatment** options.
- Recommended pesticides.
- Prevention tips.
- Expected recovery time.

If the plant looks healthy, you'll see a "healthy" result instead.

## 6. Soil fertility suggestions

Whenever a soil reading shows fertility below a healthy threshold, the platform
automatically suggests specific fixes — for example, a nitrogen deficiency will suggest
urea or vermicompost, each with an explanation of *why* it's needed, *how* to apply it, the
*expected improvement*, and the *estimated time* to see results.

## 7. History

The **History** page lists your past crop recommendations and pest scans with timestamps,
so you can track what was suggested over time and compare it against what you actually
planted.

## 8. Logging out

Tap **Logout** in the top bar at any time. Your session token is cleared from the device.
