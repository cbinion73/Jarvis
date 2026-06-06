# JARVIS CarPlay Entitlement Request

## Goal

Request Apple approval for JARVIS to expand from its current CarPlay voice-based conversational posture into a true CarPlay navigation experience.

Primary request:
- CarPlay navigation/maps entitlement for `com.binion.jarvisphone`

Current local posture:
- JARVIS already declares `com.apple.developer.carplay-voice-based-conversation`
- JARVIS already has a CarPlay scene and active CarPlay UI implementation

Relevant local files:
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/JarvisPhone.entitlements`
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/Info.plist`
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/CarPlay/CarPlaySceneDelegate.swift`
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/apps/ios/JarvisPhone/JarvisPhone/CarPlay/JarvisCarPlayController.swift`

App identity:
- App name: `JARVIS`
- Bundle ID: `com.binion.jarvisphone`
- Team ID: `LGNJ56Y22G`

## What We Are Asking Apple For

We are requesting approval for JARVIS to operate as a CarPlay navigation app because its primary in-car use is route-aware travel assistance and stop discovery.

JARVIS is not trying to mirror a general-purpose phone UI onto CarPlay. The intended CarPlay experience is driver-focused and constrained to:
- destination selection
- route-aware stop discovery
- turn-by-turn trip context
- low-distraction route refinement
- hands-free conversational assistance

## Product Summary

JARVIS is a personal travel and household intelligence system. In CarPlay, it helps the driver make safe, route-aware decisions by surfacing relevant stops and travel options that conventional map apps do not prioritize well enough for the user's needs.

Examples:
- Starbucks stops along the route
- family-friendly food stops
- gas or charging
- national parks near the route
- historical sites near the route
- saved family destinations and preferred stop categories

JARVIS already maintains route and stop state in the app, including:
- favorite destinations
- recent destinations
- active stop categories
- route-specific stop sections
- last route state

Relevant model files:
- `/Users/chris/Desktop/CODE/JARVIS/JarvisApple/Sources/JarvisKit/Models/NavigationModels.swift`

## Why Existing CarPlay Apps Are Not Sufficient

Existing CarPlay navigation apps are strong at basic routing, but JARVIS is being built for a different job:
- personalized stop intelligence
- family-specific route preferences
- curated categories such as parks and historic stops
- decision support about what stop is best, not only what stop is nearest

JARVIS is intended to reduce distraction by narrowing choices to the most relevant route-aware options instead of forcing the driver to perform multiple open-ended searches while driving.

## Safety and Driver Distraction Posture

The JARVIS CarPlay experience is designed to stay within driver-safe behavior:
- large-template CarPlay UI only
- no free-form text composition while driving
- no video playback in CarPlay UI
- no dense dashboards or general-purpose browsing
- route decisions reduced to a small number of clear choices
- voice-first posture when possible
- conversational assistance limited to travel-relevant tasks

Examples of allowed in-car actions:
- "Find the best Starbucks on my route"
- "Show family-friendly food in the next 30 miles"
- "Find national parks near this trip"
- "Navigate to the selected stop"

Examples of excluded behavior:
- general internet browsing
- arbitrary video playback in CarPlay UI
- broad non-driving workflows unrelated to travel

## Requested CarPlay Scope

We should ask Apple for approval to support:
- navigation and route guidance
- route-aware stop discovery
- voice-assisted trip refinement

We should not frame the request as:
- a broad household super-app asking for unlimited in-car access
- a dashboard replacement for the entire phone

The strongest framing is:
- JARVIS is a navigation-intelligence product with a route-aware conversational layer

## Suggested Apple Submission Copy

### Short app description

JARVIS is a personal navigation-intelligence app that helps drivers discover and select the most relevant stops along a route. It combines route guidance with personalized stop discovery for categories such as coffee, food, fuel, national parks, historical sites, and saved destinations.

### Why we need CarPlay navigation entitlement

JARVIS needs CarPlay navigation capability so drivers can safely access route-aware stop discovery and navigation guidance from the vehicle display. The app is designed to reduce distraction by showing a constrained set of high-relevance route options and enabling quick selection through CarPlay templates and voice interaction.

### What makes the app distinct

Unlike general-purpose maps that emphasize nearest-result search, JARVIS ranks route-relevant stops using the driver's saved preferences, current trip context, and stop categories. This helps the driver reach meaningful destinations such as preferred coffee stops, family food stops, national parks, and historical sites without repeated broad searches.

### Driver-safety statement

The CarPlay experience is limited to navigation-relevant tasks and uses CarPlay templates with a simplified, low-distraction interface. The app does not provide video playback, general browsing, or unrelated dashboard functionality in CarPlay. The goal is to help the driver make faster and safer trip decisions with fewer manual interactions.

## Optional Supporting Copy For Retaining Voice-Based Conversation

JARVIS also supports voice-based conversational assistance for travel-relevant tasks such as asking for route-aware stop recommendations, travel context, and destination selection. This conversational layer complements the navigation experience and helps minimize interaction while driving.

## What To Attach In The Apple Request

Apple will usually respond better if the request includes concrete evidence. Prepare:
- 3 to 6 screenshots of the current CarPlay UI
- 1 short screen recording of the CarPlay flow
- a one-page PDF showing:
  - start trip
  - ask for Starbucks or food on route
  - show curated route-aware stop results
  - select stop
  - start navigation
- a short note that the CarPlay flow excludes non-driving features

## Suggested Screenshots To Capture

1. CarPlay root view
- brief of current trip
- primary route actions

2. Stop category selection
- Starbucks
- food
- parks
- historic

3. Route-aware stop results
- small number of relevant choices
- distance from route
- route mile marker

4. Selected stop detail
- name
- address
- concise reason to choose it

5. Navigation start
- start route guidance to chosen stop

## Suggested Submission Steps

1. Sign in to Apple Developer.
2. Open Certificates, Identifiers and Profiles.
3. Select the App ID for `com.binion.jarvisphone`.
4. Use Apple's capability request flow for CarPlay.
5. Request the navigation/maps CarPlay entitlement.
6. Paste the submission copy from this document.
7. Attach screenshots and the short CarPlay video.
8. After approval, enable the capability on the App ID and regenerate profiles.

## What We Should Say If Apple Asks Why Google Maps or Waze Are Not Enough

JARVIS is not trying to duplicate a generic map app. It is focused on route-aware stop intelligence and personalized travel decision support. The core value is helping the driver safely choose the best stop for the trip context, not just the nearest stop or a generic search result.

## Recommended Entitlement Strategy

Request now:
- CarPlay navigation/maps entitlement

Retain:
- CarPlay voice-based conversation entitlement already present locally

Defer for now:
- any broader in-car media or unrelated category requests

This keeps the request focused and easier for Apple to understand.

## Practical Recommendation

Even while waiting for Apple approval:
- keep building JARVIS route intelligence
- keep external handoff to Apple Maps, Google Maps, or Waze available
- keep the CarPlay pitch focused on safe route-aware stop discovery

That gives JARVIS immediate usefulness now and a stronger case for approval later.
