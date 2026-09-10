import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createStackNavigator } from "@react-navigation/stack";

// ✅ IMPORTANT: import from screens, NOT App.js
import MainScreen from "../screens/Main";
import FileManagerScreen from "../screens/FileManagerScreen";
import EventsScreen from "../screens/EventsScreen";

const Stack = createStackNavigator();

export default function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Home"
        screenOptions={{
          headerStyle: { backgroundColor: "#020617" },
          headerTintColor: "#fff",
          headerTitleStyle: { fontWeight: "700" },
        }}
      >
        {/* 🧠 MAIN APP SCREEN */}
        <Stack.Screen
          name="Home"
          component={MainScreen}
          options={{
            title: "AutonomousSync",
          }}
        />

        {/* 📂 FILE MANAGER */}
        <Stack.Screen
          name="FileManager"
          component={FileManagerScreen}
          options={{
            title: "Your Files",
          }}
        />

        {/* 📊 EVENTS */}
        <Stack.Screen
          name="Events"
          component={EventsScreen}
          options={{
            title: "Events",
          }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}