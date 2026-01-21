import React from 'react';
import { useDashboardStats } from '../hooks/useApi';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { MessageSquare, ShoppingBag, TrendingUp, Users, Loader2 } from 'lucide-react';

export function Dashboard() {
  const { stats, loading, error } = useDashboardStats();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-12 h-12 text-primary animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <p className="text-destructive">Error cargando estadísticas: {error}</p>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Conversaciones Totales',
      value: stats?.total_conversations || 0,
      icon: MessageSquare,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Conversaciones Activas',
      value: stats?.active_conversations || 0,
      icon: Users,
      color: 'text-accent-foreground',
      bgColor: 'bg-accent/20',
    },
    {
      title: 'Productos Buscados',
      value: stats?.total_products_searched || 0,
      icon: TrendingUp,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Órdenes Generadas',
      value: stats?.total_orders || 0,
      icon: ShoppingBag,
      color: 'text-accent-foreground',
      bgColor: 'bg-accent/20',
    },
  ];

  return (
    <div className="p-6 md:p-8 space-y-8" data-testid="dashboard">
      {/* Header */}
      <div>
        <h1 className="text-4xl md:text-5xl font-heading font-bold tracking-tight mb-2">
          Dashboard
        </h1>
        <p className="text-muted-foreground text-lg">
          Estadísticas y métricas de tu asistente de moda
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <Card key={index} className="stat-card" data-testid={`stat-card-${index}`}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-heading font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="font-heading">Actividad Reciente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-muted-foreground text-center py-8">
              <p>No hay actividad reciente</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader>
            <CardTitle className="font-heading">Productos Populares</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-muted-foreground text-center py-8">
              <p>Aún no hay datos de productos</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}