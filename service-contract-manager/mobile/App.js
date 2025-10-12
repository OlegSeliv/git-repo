import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Provider as PaperProvider, MD3LightTheme, configureFonts } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Импорт экранов
import HomeScreen from './src/screens/HomeScreen';
import ContractsScreen from './src/screens/ContractsScreen';
import OrdersScreen from './src/screens/OrdersScreen';
import MaterialsScreen from './src/screens/MaterialsScreen';
import TripsScreen from './src/screens/TripsScreen';
import DocumentsScreen from './src/screens/DocumentsScreen';
import ContractDetailScreen from './src/screens/ContractDetailScreen';
import OrderDetailScreen from './src/screens/OrderDetailScreen';
import TripDetailScreen from './src/screens/TripDetailScreen';
import SettingsScreen from './src/screens/SettingsScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

// Настройка темы
const theme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#1890ff',
    accent: '#52c41a',
  },
};

// Стек навигации для контрактов
function ContractsStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen 
        name="ContractsList" 
        component={ContractsScreen} 
        options={{ title: 'Контракты' }}
      />
      <Stack.Screen 
        name="ContractDetail" 
        component={ContractDetailScreen} 
        options={{ title: 'Детали контракта' }}
      />
    </Stack.Navigator>
  );
}

// Стек навигации для заказов
function OrdersStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen 
        name="OrdersList" 
        component={OrdersScreen} 
        options={{ title: 'Заказы' }}
      />
      <Stack.Screen 
        name="OrderDetail" 
        component={OrderDetailScreen} 
        options={{ title: 'Детали заказа' }}
      />
    </Stack.Navigator>
  );
}

// Стек навигации для командировок
function TripsStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen 
        name="TripsList" 
        component={TripsScreen} 
        options={{ title: 'Командировки' }}
      />
      <Stack.Screen 
        name="TripDetail" 
        component={TripDetailScreen} 
        options={{ title: 'Детали командировки' }}
      />
    </Stack.Navigator>
  );
}

export default function App() {
  const [serverUrl, setServerUrl] = useState('http://localhost:8000');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const url = await AsyncStorage.getItem('serverUrl');
      if (url) {
        setServerUrl(url);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  return (
    <PaperProvider theme={theme}>
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            tabBarIcon: ({ focused, color, size }) => {
              let iconName;

              switch (route.name) {
                case 'Home':
                  iconName = 'view-dashboard';
                  break;
                case 'Contracts':
                  iconName = 'file-document';
                  break;
                case 'Orders':
                  iconName = 'cart';
                  break;
                case 'Materials':
                  iconName = 'package-variant';
                  break;
                case 'Trips':
                  iconName = 'map-marker';
                  break;
                case 'Documents':
                  iconName = 'folder';
                  break;
                default:
                  iconName = 'circle';
              }

              return <Icon name={iconName} size={size} color={color} />;
            },
            tabBarActiveTintColor: '#1890ff',
            tabBarInactiveTintColor: 'gray',
          })}
        >
          <Tab.Screen 
            name="Home" 
            component={HomeScreen} 
            options={{ title: 'Главная' }}
          />
          <Tab.Screen 
            name="Contracts" 
            component={ContractsStack} 
            options={{ title: 'Контракты', headerShown: false }}
          />
          <Tab.Screen 
            name="Orders" 
            component={OrdersStack} 
            options={{ title: 'Заказы', headerShown: false }}
          />
          <Tab.Screen 
            name="Materials" 
            component={MaterialsScreen} 
            options={{ title: 'Материалы' }}
          />
          <Tab.Screen 
            name="Trips" 
            component={TripsStack} 
            options={{ title: 'Командировки', headerShown: false }}
          />
          <Tab.Screen 
            name="Documents" 
            component={DocumentsScreen} 
            options={{ title: 'Документы' }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </PaperProvider>
  );
}