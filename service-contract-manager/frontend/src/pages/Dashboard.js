import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress, List, Alert, Spin } from 'antd';
import {
  FileTextOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  DollarOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  ToolOutlined
} from '@ant-design/icons';
import { Pie, Line, Column } from '@ant-design/charts';
import axios from 'axios';

const Dashboard = ({ showNotification }) => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 60000); // Обновление каждую минуту
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/analytics/dashboard');
      setDashboardData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки данных дашборда:', error);
      showNotification('error', 'Ошибка', 'Не удалось загрузить данные дашборда');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="Загрузка данных..." />
      </div>
    );
  }

  if (!dashboardData) {
    return <Alert message="Нет данных" type="warning" />;
  }

  const { 
    contracts, 
    orders, 
    business_trips, 
    materials, 
    critical_materials,
    upcoming_tasks,
    monthly_finance,
    orders_by_location,
    devices_at_factory
  } = dashboardData;

  // Подготовка данных для графика контрактов
  const contractsPieData = [
    { type: 'Активные', value: contracts.active_contracts || 0 },
    { type: 'Завершенные', value: contracts.completed_contracts || 0 }
  ];

  const contractsPieConfig = {
    data: contractsPieData,
    angleField: 'value',
    colorField: 'type',
    radius: 0.8,
    label: {
      type: 'inner',
      offset: '-30%',
      content: '{value}',
      style: {
        fontSize: 14,
        textAlign: 'center',
      },
    },
    interactions: [{ type: 'element-active' }],
  };

  // Подготовка данных для графика заказов
  const ordersColumnData = [
    { status: 'Новые', count: orders.new_orders || 0 },
    { status: 'В работе', count: orders.in_progress_orders || 0 },
    { status: 'Завершены', count: orders.completed_orders || 0 },
    { status: 'Задержаны', count: orders.delayed_orders || 0 }
  ];

  const ordersColumnConfig = {
    data: ordersColumnData,
    xField: 'status',
    yField: 'count',
    label: {
      position: 'middle',
      style: {
        fill: '#FFFFFF',
        opacity: 0.6,
      },
    },
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: false,
      },
    },
  };

  const criticalMaterialsColumns = [
    {
      title: 'Наименование',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Артикул',
      dataIndex: 'article',
      key: 'article',
    },
    {
      title: 'На складе',
      dataIndex: 'quantity_warehouse',
      key: 'quantity_warehouse',
      render: (value) => `${value} шт`
    },
    {
      title: 'Минимум',
      dataIndex: 'quantity_minimum',
      key: 'quantity_minimum',
      render: (value) => `${value} шт`
    },
    {
      title: 'Дефицит',
      dataIndex: 'deficit_amount',
      key: 'deficit_amount',
      render: (value) => (
        <Tag color="red">{value} шт</Tag>
      )
    }
  ];

  const ordersByLocationColumns = [
    {
      title: 'Локация',
      dataIndex: 'location',
      key: 'location',
      ellipsis: true,
    },
    {
      title: 'Всего заказов',
      dataIndex: 'order_count',
      key: 'order_count',
      width: 120,
    },
    {
      title: 'Активных',
      dataIndex: 'active_orders',
      key: 'active_orders',
      width: 100,
      render: (value) => <Tag color="blue">{value}</Tag>
    }
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5' }}>
      <h2>Главная панель управления</h2>
      
      {/* Основные показатели */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Активные контракты"
              value={contracts.active_contracts || 0}
              prefix={<FileTextOutlined />}
              suffix={`из ${contracts.total_contracts || 0}`}
            />
            <Progress 
              percent={Math.round((contracts.active_contracts / contracts.total_contracts) * 100) || 0} 
              strokeColor="#52c41a"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Заказы в работе"
              value={orders.in_progress_orders || 0}
              prefix={<ShoppingCartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            {orders.delayed_orders > 0 && (
              <Alert
                message={`Задержано: ${orders.delayed_orders}`}
                type="warning"
                showIcon
                banner
                style={{ marginTop: '8px' }}
              />
            )}
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Активные командировки"
              value={business_trips.total_active_trips || 0}
              prefix={<EnvironmentOutlined />}
              suffix={`${business_trips.employees_on_trip || 0} сотр.`}
            />
            <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
              Локаций: {business_trips.unique_locations || 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Дефицит материалов"
              value={materials.deficit_items || 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: materials.deficit_items > 0 ? '#cf1322' : '#52c41a' }}
            />
            <Progress 
              percent={Math.round((materials.deficit_items / materials.total_items) * 100) || 0} 
              strokeColor="#ff4d4f"
              showInfo={false}
            />
          </Card>
        </Col>
      </Row>

      {/* Финансовые показатели */}
      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={8}>
          <Card title="Финансовый статус (все контракты)">
            <Statistic
              title="Общая стоимость"
              value={contracts.total_value || 0}
              precision={2}
              suffix="₽"
            />
            <Statistic
              title="Получено"
              value={contracts.total_received || 0}
              precision={2}
              suffix="₽"
              valueStyle={{ color: '#52c41a' }}
            />
            <Statistic
              title="К получению"
              value={contracts.total_pending || 0}
              precision={2}
              suffix="₽"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Платежи за месяц">
            <Statistic
              title="Авансы"
              value={monthly_finance?.advance_received || 0}
              precision={2}
              suffix="₽"
              prefix={<DollarOutlined />}
            />
            <Statistic
              title="Окончательные расчеты"
              value={monthly_finance?.final_received || 0}
              precision={2}
              suffix="₽"
              valueStyle={{ color: '#52c41a' }}
            />
            <Statistic
              title="Расходы"
              value={monthly_finance?.expenses || 0}
              precision={2}
              suffix="₽"
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Устройства на заводе">
            <Statistic
              title="Всего на ремонте"
              value={devices_at_factory?.total_devices || 0}
              prefix={<ToolOutlined />}
            />
            <Row>
              <Col span={12}>
                <Statistic
                  title="В работе"
                  value={devices_at_factory?.in_repair || 0}
                  valueStyle={{ fontSize: '16px', color: '#1890ff' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Ожидают запчасти"
                  value={devices_at_factory?.waiting_parts || 0}
                  valueStyle={{ fontSize: '16px', color: '#faad14' }}
                />
              </Col>
            </Row>
            <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
              Среднее время ремонта: {Math.round(devices_at_factory?.avg_days_in_repair || 0)} дней
            </div>
          </Card>
        </Col>
      </Row>

      {/* Графики и таблицы */}
      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={8}>
          <Card title="Распределение контрактов">
            <Pie {...contractsPieConfig} height={200} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Статусы заказов">
            <Column {...ordersColumnConfig} height={200} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Предстоящие задачи">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="Всего"
                  value={upcoming_tasks?.total_tasks || 0}
                  prefix={<ClockCircleOutlined />}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Срочные"
                  value={upcoming_tasks?.urgent_tasks || 0}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Просроченные"
                  value={upcoming_tasks?.overdue_tasks || 0}
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
            </Row>
            {upcoming_tasks?.overdue_tasks > 0 && (
              <Alert
                message="Есть просроченные задачи!"
                description="Проверьте раздел 'Задачи' для детальной информации"
                type="error"
                showIcon
                style={{ marginTop: '16px' }}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* Критические материалы и заказы по локациям */}
      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={12}>
          <Card title="Критические материалы (требуют пополнения)">
            {critical_materials && critical_materials.length > 0 ? (
              <Table
                dataSource={critical_materials}
                columns={criticalMaterialsColumns}
                pagination={false}
                size="small"
                rowKey="article"
              />
            ) : (
              <Alert
                message="Отличные новости!"
                description="Нет материалов с критическим уровнем запасов"
                type="success"
                showIcon
              />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Заказы по локациям">
            <Table
              dataSource={orders_by_location}
              columns={ordersByLocationColumns}
              pagination={false}
              size="small"
              rowKey="location"
              scroll={{ y: 300 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Информационная панель */}
      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={24}>
          <Card title="Сводка по системе">
            <Row gutter={16}>
              <Col span={6}>
                <Alert
                  message="Контракты"
                  description={`${contracts.active_contracts || 0} активных из ${contracts.total_contracts || 0}`}
                  type="info"
                  showIcon
                />
              </Col>
              <Col span={6}>
                <Alert
                  message="Заказы"
                  description={`${orders.in_progress_orders || 0} в работе из ${orders.total_orders || 0}`}
                  type="info"
                  showIcon
                />
              </Col>
              <Col span={6}>
                <Alert
                  message="Командировки"
                  description={`${business_trips.employees_on_trip || 0} сотрудников в ${business_trips.unique_locations || 0} локациях`}
                  type="info"
                  showIcon
                />
              </Col>
              <Col span={6}>
                <Alert
                  message="Склад"
                  description={`${materials.deficit_items || 0} позиций требуют пополнения`}
                  type={materials.deficit_items > 0 ? 'warning' : 'success'}
                  showIcon
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;