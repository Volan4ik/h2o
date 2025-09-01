import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { TrendingUp, Calendar, Droplets } from "lucide-react";

interface DayData {
  date: string;
  ml: number;
}

interface WeeklyStatsProps {
  days: DayData[];
  goalMl: number;
}

export function WeeklyStats({ days, goalMl }: WeeklyStatsProps) {
  // Вычисляем статистику
  const totalMl = days.reduce((sum, day) => sum + day.ml, 0);
  const activeDays = days.filter(day => day.ml > 0).length;
  const averageMl = activeDays > 0 ? Math.round(totalMl / activeDays) : 0;
  const goalDays = days.filter(day => day.ml >= goalMl).length;
  const goalPercentage = activeDays > 0 ? Math.round((goalDays / activeDays) * 100) : 0;
  
  // Находим лучший и худший дни (только среди активных дней)
  const activeDaysData = days.filter(day => day.ml > 0);
  const bestDay = activeDaysData.length > 0 
    ? activeDaysData.reduce((best, day) => day.ml > best.ml ? day : best, activeDaysData[0])
    : days[0];
  const worstDay = activeDaysData.length > 0 
    ? activeDaysData.reduce((worst, day) => day.ml < worst.ml ? day : worst, activeDaysData[0])
    : days[0];
  
  // Форматируем даты
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { 
      weekday: 'short', 
      day: 'numeric',
      month: 'short'
    });
  };
  

  
  // Создаем точки для плавной кривой
  const maxValue = Math.max(...days.map(d => d.ml), goalMl);
  const createSmoothCurvePath = () => {
    if (days.length < 2) return '';
    
    const points = days.map((day, index) => {
      const x = (index / (days.length - 1)) * 100;
      const y = 100 - (day.ml / maxValue) * 80; // 80% высоты для кривой
      return { x, y };
    });
    
    let path = `M ${points[0].x},${points[0].y}`;
    
    for (let i = 1; i < points.length; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const next = points[i + 1];
      
      if (next) {
        // Кривая Безье для плавности
        const cp1x = prev.x + (curr.x - prev.x) / 3;
        const cp1y = prev.y;
        const cp2x = curr.x - (next.x - curr.x) / 3;
        const cp2y = curr.y;
        
        path += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${curr.x},${curr.y}`;
      } else {
        // Последняя точка - прямая линия
        path += ` L ${curr.x},${curr.y}`;
      }
    }
    
    return path;
  };

  const curvePath = createSmoothCurvePath();

  return (
    <Card className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-blue-500" />
          Недельная статистика
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Общая статистика */}
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-3 bg-blue-50 rounded-lg mb-4">
            <div className="text-2xl font-bold text-blue-600">{averageMl} мл</div>
            <div className="text-sm text-gray-600">Среднее в день</div>
          </div>
        </div>

        {/* Достижения */}
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-3 bg-gradient-to-r from-green-50 to-green-100 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-green-800">Лучший день</span>
            </div>
            <div className="text-2xl font-bold text-green-700">{bestDay.ml} мл</div>
            <div className="text-xs text-green-600">{formatDate(bestDay.date)}</div>
          </div>
          
          <div className="text-center p-3 bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg border border-orange-200">
            <div className="flex items-center gap-2 mb-1">
              <Droplets className="h-4 w-4 text-orange-600" />
              <span className="text-sm font-medium text-orange-800">Худший день</span>
            </div>
            <div className="text-2xl font-bold text-orange-700">{worstDay.ml} мл</div>
            <div className="text-xs text-orange-600">{formatDate(worstDay.date)}</div>
          </div>
        </div>


      </CardContent>
    </Card>
  );
}
