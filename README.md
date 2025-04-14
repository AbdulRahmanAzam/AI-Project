# 🧭 AI-Powered Campus Navigator
**Smart Path Search Application for University Navigation**

## 📌 Project Overview
The **AI-Powered Campus Navigator** is a smart navigation app designed for university students and staff. It helps users find the shortest path between their current location and destination across campus using AI-based search algorithms. The application supports both **outdoor navigation** (between buildings) and **indoor navigation** (within multi-floor buildings).

---

## 🎯 Objectives
- Develop an intelligent navigation system tailored for university campuses.
- Implement AI-based pathfinding algorithms for efficient and accurate route planning.
- Provide an intuitive user experience with clear visual path guidance.
- Support multi-level navigation by expanding the traditional 2D search space into a 3D environment (floors and rooms).

---

## 🧠 AI-Driven Decision-Making
The application incorporates intelligent algorithms for decision-making and dynamic path planning.

### 🔍 Search Algorithms:
- **A\***: For outdoor shortest pathfinding between campus buildings.
- **Dijkstra’s Algorithm / BFS**: For detailed indoor navigation within building floors.

### 🗺️ Graph-Based Representation:
- Nodes: Entrances, rooms, staircases, etc.
- Edges: Walkable paths between nodes.

### 🤖 Smart Decisions:
- Choose optimal paths in real-time.
- Avoid blocked or restricted areas.
- Adjust paths dynamically based on user movement (future enhancement).

---

## 🌐 Expansion of Search Space
Traditional pathfinding works on 2D grids. Our app extends this to:
- Multiple building floors.
- Indoor navigation (rooms, corridors).
- Entry/exit transitions across different layers.

This approach models **multi-layered graph searches**, reflecting real-world complexity and enhancing usability.

---

## 🔐 Constraint Satisfaction Problems (CSPs)
To handle more realistic navigation requirements, CSPs are integrated to:
- Avoid restricted areas or walls.
- Respect access rules (e.g., lab hours).
- Bypass temporarily closed paths or dynamic obstacles.

---

## 🖼️ User Interface (UI)
- Interactive map of the campus.
- Users can select their current location and destination.
- The optimal path is highlighted on the map.
- Intuitive and responsive design for ease of use.

---

## 🛠️ Tools and Technologies

| Component            | Technology              |
|---------------------|--------------------------|
| Programming Language | Python |
| Graph Search Library | NetworkX                |
| Map Rendering        | MapBox API              |
| Platform             | Android/iOS (cross-platform) |

---

## ✅ Conclusion
The **AI-Powered Campus Navigator** leverages artificial intelligence and constraint satisfaction to solve real-world navigation challenges on university campuses. By integrating multi-floor routing, CSP handling, and a friendly UI, it significantly improves the accessibility and convenience for users. This project represents a robust and innovative solution in the domain of AI-driven smart campus systems.

---
