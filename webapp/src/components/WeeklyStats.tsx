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
  const averageMl = Math.round(totalMl / days.length);
  const goalDays = days.filter(day => day.ml >= goalMl).length;
  const goalPercentage = Math.round((goalDays / days.length) * 100);
  
  // Находим лучший и худший дни
  const bestDay = days.reduce((best, day) => day.ml > best.ml ? day : best, days[0]);
  const worstDay = days.reduce((worst, day) => day.ml < worst.ml ? day : worst, days[0]);
  
  // Форматируем даты
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', { 
      weekday: 'short', 
      day: 'numeric',
      month: 'short'
    });
  };
  
  // Получаем цвет для дня в зависимости от прогресса
  const getDayColor = (ml: number) => {
    const percentage = (ml / goalMl) * 100;
    if (percentage >= 100) return "bg-green-500";
    if (percentage >= 80) return "bg-blue-500";
    if (percentage >= 60) return "bg-yellow-500";
    if (percentage >= 40) return "bg-orange-500";
    return "bg-red-500";
  };
  
  // Получаем высоту столбца (максимум 120px)
  const getBarHeight = (ml: number) => {
    const percentage = Math.min((ml / goalMl) * 100, 100);
    return Math.max((percentage / 100) * 120, 8); // минимум 8px для видимости
  };

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
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{averageMl}мл</div>
            <div className="text-sm text-gray-600">Среднее в день</div>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{goalPercentage}%</div>
            <div className="text-sm text-gray-600">Дней с целью</div>
          </div>
        </div>

        {/* График дней */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Потребление по дням</h4>
          <div className="flex items-end justify-between gap-2 h-32">
            {days.map((day, index) => (
              <div key={day.date} className="flex flex-col items-center flex-1">
                {/* Столбец */}
                <div className="relative w-full flex justify-center">
                  <div
                    className={`w-6 rounded-t-md transition-all duration-700 ease-out ${getDayColor(day.ml)}`}
                    style={{ 
                      height: `${getBarHeight(day.ml)}px`,
                      animationDelay: `${index * 100}ms`
                    }}
                  >
                    {/* Всплывающая подсказка */}
                    <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 hover:opacity-100 transition-opacity whitespace-nowrap">
                      {day.ml}мл
                    </div>
                  </div>
                </div>
                
                {/* Дата */}
                <div className="text-xs text-gray-500 mt-2 text-center leading-tight">
                  {formatDate(day.date)}
                </div>
                
                {/* Количество мл */}
                <div className="text-xs font-medium text-gray-700 mt-1">
                  {day.ml}мл
                </div>
              </div>
            ))}
          </div>
          
          {/* Линия цели */}
          <div className="relative mt-2">
            <div className="absolute top-0 left-0 right-0 h-px bg-gray-300"></div>
            <div className="absolute top-0 left-0 right-0 h-px bg-green-400 opacity-50" style={{ 
              height: '2px',
              top: `${120 - (goalMl / Math.max(...days.map(d => d.ml), goalMl)) * 120}px`
            }}></div>
            <div className="text-xs text-green-600 text-center mt-1">Цель: {goalMl}мл</div>
          </div>
        </div>

        {/* Достижения */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-gradient-to-r from-green-50 to-green-100 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-green-800">Лучший день</span>
            </div>
            <div className="text-lg font-bold text-green-700">{bestDay.ml}мл</div>
            <div className="text-xs text-green-600">{formatDate(bestDay.date)}</div>
          </div>
          
          <div className="p-3 bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg border border-orange-200">
            <div className="flex items-center gap-2 mb-1">
              <Droplets className="h-4 w-4 text-orange-600" />
              <span className="text-sm font-medium text-orange-800">Худший день</span>
            </div>
            <div className="text-lg font-bold text-orange-700">{worstDay.ml}мл</div>
            <div className="text-xs text-orange-600">{formatDate(worstDay.date)}</div>
          </div>
        </div>

        {/* Мотивационное сообщение */}
        <div className="text-center p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
          {goalPercentage >= 80 ? (
            <div className="text-green-700">
              <div className="text-2xl mb-2">🏆</div>
              <div className="font-semibold">Отличная работа!</div>
              <div className="text-sm">Вы достигли цели в {goalDays} из {days.length} дней!</div>
            </div>
          ) : goalPercentage >= 60 ? (
            <div className="text-blue-700">
              <div className="text-2xl mb-2">💪</div>
              <div className="font-semibold">Хороший прогресс!</div>
              <div className="text-sm">Продолжайте в том же духе!</div>
            </div>
          ) : (
            <div className="text-orange-700">
              <div className="text-2xl mb-2">💧</div>
              <div className="font-semibold">Можно лучше!</div>
              <div className="text-sm">Попробуйте пить больше воды каждый день</div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
