import React, { useState, useEffect } from 'react';
import { Layout, Menu, Badge, notification, ConfigProvider } from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  DollarOutlined,
  FolderOutlined,
  BarChartOutlined,
  BellOutlined,
  ToolOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import ruRU from 'antd/locale/ru_RU';
import 'antd/dist/reset.css';
import './App.css';

// Импорт компонентов страниц
import Dashboard from './pages/Dashboard';
import Contracts from './pages/Contracts';
import Orders from './pages/Orders';
import Materials from './pages/Materials';
import BusinessTrips from './pages/BusinessTrips';
import Financial from './pages/Financial';
import Documents from './pages/Documents';
import Analytics from './pages/Analytics';
import Tasks from './pages/Tasks';
import Settings from './pages/Settings';

const { Header, Sider, Content } = Layout;

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Загрузка уведомлений
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000); // Обновление каждые 30 секунд
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/notifications');
      const data = await response.json();
      setNotifications(data);
      setUnreadCount(data.filter(n => !n.is_read).length);
    } catch (error) {
      console.error('Ошибка загрузки уведомлений:', error);
    }
  };

  const showNotification = (type, message, description) => {
    notification[type]({
      message: message,
      description: description,
      placement: 'topRight',
    });
  };

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/dashboard">Главная панель</Link>,
    },
    {
      key: 'contracts',
      icon: <FileTextOutlined />,
      label: <Link to="/contracts">Контракты</Link>,
    },
    {
      key: 'orders',
      icon: <ShoppingCartOutlined />,
      label: <Link to="/orders">Заказы</Link>,
    },
    {
      key: 'materials',
      icon: <ToolOutlined />,
      label: <Link to="/materials">Материалы и склад</Link>,
    },
    {
      key: 'business-trips',
      icon: <EnvironmentOutlined />,
      label: <Link to="/business-trips">Командировки</Link>,
    },
    {
      key: 'financial',
      icon: <DollarOutlined />,
      label: <Link to="/financial">Финансы</Link>,
    },
    {
      key: 'documents',
      icon: <FolderOutlined />,
      label: <Link to="/documents">Документы</Link>,
    },
    {
      key: 'tasks',
      icon: <TeamOutlined />,
      label: <Link to="/tasks">Задачи</Link>,
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: <Link to="/analytics">Аналитика</Link>,
    },
  ];

  return (
    <ConfigProvider locale={ruRU}>
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Sider 
            collapsible 
            collapsed={collapsed} 
            onCollapse={setCollapsed}
            width={250}
          >
            <div className="logo">
              <h3 style={{ color: 'white', padding: '16px', margin: 0 }}>
                {collapsed ? 'СУК' : 'Сервисные контракты'}
              </h3>
            </div>
            <Menu 
              theme="dark" 
              defaultSelectedKeys={['dashboard']} 
              mode="inline"
              items={menuItems}
            />
          </Sider>
          <Layout>
            <Header style={{ 
              background: '#fff', 
              padding: '0 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: '0 1px 4px rgba(0,21,41,.08)'
            }}>
              <h2 style={{ margin: 0 }}>Система управления сервисными контрактами</h2>
              <Badge count={unreadCount}>
                <BellOutlined style={{ fontSize: '20px', cursor: 'pointer' }} />
              </Badge>
            </Header>
            <Content style={{ margin: '16px' }}>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" />} />
                <Route path="/dashboard" element={<Dashboard showNotification={showNotification} />} />
                <Route path="/contracts/*" element={<Contracts showNotification={showNotification} />} />
                <Route path="/orders/*" element={<Orders showNotification={showNotification} />} />
                <Route path="/materials" element={<Materials showNotification={showNotification} />} />
                <Route path="/business-trips" element={<BusinessTrips showNotification={showNotification} />} />
                <Route path="/financial" element={<Financial showNotification={showNotification} />} />
                <Route path="/documents" element={<Documents showNotification={showNotification} />} />
                <Route path="/tasks" element={<Tasks showNotification={showNotification} />} />
                <Route path="/analytics" element={<Analytics showNotification={showNotification} />} />
                <Route path="/settings" element={<Settings showNotification={showNotification} />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;