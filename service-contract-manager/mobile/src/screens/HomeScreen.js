import React, { useState, useEffect } from 'react';
import { View, ScrollView, RefreshControl, StyleSheet } from 'react-native';
import { Card, Title, Paragraph, Text, Surface, Divider, Chip, ActivityIndicator, Banner } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const HomeScreen = ({ navigation }) => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [serverUrl, setServerUrl] = useState('http://localhost:8000');
  const [error, setError] = useState(null);

  useEffect(() => {
    loadServerUrl();
  }, []);

  useEffect(() => {
    if (serverUrl) {
      fetchDashboardData();
    }
  }, [serverUrl]);

  const loadServerUrl = async () => {
    try {
      const url = await AsyncStorage.getItem('serverUrl');
      if (url) {
        setServerUrl(url);
      }
    } catch (error) {
      console.error('Error loading server URL:', error);
    }
  };

  const fetchDashboardData = async () => {
    try {
      setError(null);
      const response = await axios.get(`${serverUrl}/api/analytics/dashboard`);
      setDashboardData(response.data);
      setLoading(false);
      setRefreshing(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError('Не удалось загрузить данные. Проверьте подключение к серверу.');
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" />
        <Text style={styles.loadingText}>Загрузка данных...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Banner
          visible={true}
          icon="alert"
          actions={[
            {
              label: 'Повторить',
              onPress: fetchDashboardData,
            },
          ]}
        >
          {error}
        </Banner>
      </View>
    );
  }

  if (!dashboardData) {
    return (
      <View style={styles.centerContainer}>
        <Text>Нет данных для отображения</Text>
      </View>
    );
  }

  const { contracts, orders, business_trips, materials, critical_materials, upcoming_tasks, devices_at_factory } = dashboardData;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Основные показатели */}
      <Title style={styles.sectionTitle}>Основные показатели</Title>
      
      <View style={styles.statsRow}>
        <Card style={styles.statCard}>
          <Card.Content>
            <View style={styles.statHeader}>
              <Icon name="file-document" size={24} color="#1890ff" />
              <Text style={styles.statValue}>{contracts?.active_contracts || 0}</Text>
            </View>
            <Text style={styles.statLabel}>Активных контрактов</Text>
            <Text style={styles.statSubLabel}>из {contracts?.total_contracts || 0}</Text>
          </Card.Content>
        </Card>

        <Card style={styles.statCard}>
          <Card.Content>
            <View style={styles.statHeader}>
              <Icon name="cart" size={24} color="#52c41a" />
              <Text style={styles.statValue}>{orders?.in_progress_orders || 0}</Text>
            </View>
            <Text style={styles.statLabel}>Заказов в работе</Text>
            <Text style={styles.statSubLabel}>всего: {orders?.total_orders || 0}</Text>
          </Card.Content>
        </Card>
      </View>

      <View style={styles.statsRow}>
        <Card style={styles.statCard}>
          <Card.Content>
            <View style={styles.statHeader}>
              <Icon name="map-marker" size={24} color="#faad14" />
              <Text style={styles.statValue}>{business_trips?.total_active_trips || 0}</Text>
            </View>
            <Text style={styles.statLabel}>Командировок</Text>
            <Text style={styles.statSubLabel}>{business_trips?.employees_on_trip || 0} сотр.</Text>
          </Card.Content>
        </Card>

        <Card style={styles.statCard}>
          <Card.Content>
            <View style={styles.statHeader}>
              <Icon name="alert" size={24} color={materials?.deficit_items > 0 ? "#ff4d4f" : "#52c41a"} />
              <Text style={styles.statValue}>{materials?.deficit_items || 0}</Text>
            </View>
            <Text style={styles.statLabel}>Дефицит материалов</Text>
            <Text style={styles.statSubLabel}>позиций</Text>
          </Card.Content>
        </Card>
      </View>

      {/* Финансовая сводка */}
      <Title style={styles.sectionTitle}>Финансы</Title>
      <Card style={styles.fullCard}>
        <Card.Content>
          <View style={styles.financeRow}>
            <Text style={styles.financeLabel}>Общая стоимость контрактов:</Text>
            <Text style={styles.financeValue}>{(contracts?.total_value || 0).toFixed(2)} ₽</Text>
          </View>
          <Divider style={styles.divider} />
          <View style={styles.financeRow}>
            <Text style={styles.financeLabel}>Получено средств:</Text>
            <Text style={[styles.financeValue, { color: '#52c41a' }]}>
              {(contracts?.total_received || 0).toFixed(2)} ₽
            </Text>
          </View>
          <Divider style={styles.divider} />
          <View style={styles.financeRow}>
            <Text style={styles.financeLabel}>К получению:</Text>
            <Text style={[styles.financeValue, { color: '#faad14' }]}>
              {(contracts?.total_pending || 0).toFixed(2)} ₽
            </Text>
          </View>
        </Card.Content>
      </Card>

      {/* Устройства на заводе */}
      <Title style={styles.sectionTitle}>Устройства на ремонте</Title>
      <Card style={styles.fullCard}>
        <Card.Content>
          <View style={styles.deviceRow}>
            <Icon name="wrench" size={20} color="#1890ff" />
            <Text style={styles.deviceText}>
              Всего на заводе: {devices_at_factory?.total_devices || 0}
            </Text>
          </View>
          <View style={styles.deviceRow}>
            <Icon name="progress-wrench" size={20} color="#52c41a" />
            <Text style={styles.deviceText}>
              В работе: {devices_at_factory?.in_repair || 0}
            </Text>
          </View>
          <View style={styles.deviceRow}>
            <Icon name="clock-outline" size={20} color="#faad14" />
            <Text style={styles.deviceText}>
              Ожидают запчасти: {devices_at_factory?.waiting_parts || 0}
            </Text>
          </View>
          {devices_at_factory?.avg_days_in_repair && (
            <Text style={styles.avgTime}>
              Среднее время ремонта: {Math.round(devices_at_factory.avg_days_in_repair)} дней
            </Text>
          )}
        </Card.Content>
      </Card>

      {/* Предстоящие задачи */}
      <Title style={styles.sectionTitle}>Задачи</Title>
      <Card style={styles.fullCard}>
        <Card.Content>
          <View style={styles.tasksRow}>
            <Chip mode="outlined" style={styles.taskChip}>
              Всего: {upcoming_tasks?.total_tasks || 0}
            </Chip>
            <Chip mode="outlined" style={[styles.taskChip, { backgroundColor: '#fff3cd' }]}>
              Срочные: {upcoming_tasks?.urgent_tasks || 0}
            </Chip>
            <Chip mode="outlined" style={[styles.taskChip, { backgroundColor: '#f8d7da' }]}>
              Просроченные: {upcoming_tasks?.overdue_tasks || 0}
            </Chip>
          </View>
        </Card.Content>
      </Card>

      {/* Критические материалы */}
      {critical_materials && critical_materials.length > 0 && (
        <>
          <Title style={styles.sectionTitle}>Критические материалы</Title>
          <Card style={styles.fullCard}>
            <Card.Content>
              {critical_materials.slice(0, 3).map((material, index) => (
                <View key={index}>
                  <View style={styles.materialRow}>
                    <View style={styles.materialInfo}>
                      <Text style={styles.materialName}>{material.name}</Text>
                      <Text style={styles.materialArticle}>{material.article}</Text>
                    </View>
                    <View style={styles.materialStock}>
                      <Text style={styles.stockText}>На складе: {material.quantity_warehouse}</Text>
                      <Text style={[styles.stockText, { color: '#ff4d4f' }]}>
                        Дефицит: {material.deficit_amount}
                      </Text>
                    </View>
                  </View>
                  {index < critical_materials.length - 1 && <Divider style={styles.divider} />}
                </View>
              ))}
            </Card.Content>
          </Card>
        </>
      )}

      <View style={styles.bottomSpace} />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 8,
  },
  statsRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  statCard: {
    flex: 1,
    marginHorizontal: 4,
  },
  statHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  statLabel: {
    fontSize: 14,
    color: '#666',
  },
  statSubLabel: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  fullCard: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  financeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  financeLabel: {
    fontSize: 14,
    color: '#666',
  },
  financeValue: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  divider: {
    marginVertical: 4,
  },
  deviceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
  },
  deviceText: {
    marginLeft: 12,
    fontSize: 14,
    color: '#333',
  },
  avgTime: {
    marginTop: 8,
    fontSize: 12,
    color: '#666',
    fontStyle: 'italic',
  },
  tasksRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  taskChip: {
    marginRight: 8,
    marginBottom: 8,
  },
  materialRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  materialInfo: {
    flex: 1,
  },
  materialName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  materialArticle: {
    fontSize: 12,
    color: '#666',
  },
  materialStock: {
    alignItems: 'flex-end',
  },
  stockText: {
    fontSize: 12,
    color: '#666',
  },
  bottomSpace: {
    height: 20,
  },
})

export default HomeScreen;