import React, { useState, useEffect } from "react";
import { WaterBottle } from "./components/WaterBottle";
import { WeeklyStats } from "./components/WeeklyStats";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Droplets, Plus, Minus, RotateCcw } from "lucide-react";

const API_BASE = (import.meta as any).env?.VITE_API_URL || "";
const tg = (window as any).Telegram?.WebApp;

export default function App() {
  const [currentWater, setCurrentWater] = useState(0);
  const [dailyGoal, setDailyGoal] = useState(2000);
  const [defaultGlass, setDefaultGlass] = useState(250);
  const [progress, setProgress] = useState(0);
  const [isGoalReached, setIsGoalReached] = useState(false);
  const [weeklyStats, setWeeklyStats] = useState<{days: Array<{date: string, ml: number}>, goal_ml: number} | null>(null);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [newGoal, setNewGoal] = useState(2000);

  // --- загрузка текущих данных ---
  async function loadToday() {
    const r = await fetch(`${API_BASE}/api/webapp/today`, {
      headers: { "X-Tg-Init-Data": tg?.initData || "" },
    });
    if (!r.ok) return;
    const data = await r.json();
    setCurrentWater(data.consumed_ml);
    setDailyGoal(data.goal_ml);
    setDefaultGlass(data.default_glass_ml);
    const pct = Math.min((data.consumed_ml / data.goal_ml) * 100, 100);
    setProgress(pct);
    setIsGoalReached(data.consumed_ml >= data.goal_ml);
  }

  // --- загрузка недельной статистики ---
  async function loadWeeklyStats() {
    const r = await fetch(`${API_BASE}/api/webapp/stats/days?days=7`, {
      headers: { "X-Tg-Init-Data": tg?.initData || "" },
    });
    if (!r.ok) return;
    const data = await r.json();
    setWeeklyStats(data);
  }

  // --- добавление воды (положительное или отрицательное) ---
  async function addWater(amount: number) {
    await fetch(`${API_BASE}/api/webapp/log`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tg-Init-Data": tg?.initData || "",
      },
      body: JSON.stringify({ amount_ml: amount }),
    });
    await loadToday();
    await loadWeeklyStats(); // Обновляем статистику после изменения
  }

  // --- сброс прогресса ---
  async function resetWater() {
    await fetch(`${API_BASE}/api/webapp/reset`, {
      method: "POST",
      headers: { "X-Tg-Init-Data": tg?.initData || "" },
    });
    await loadToday();
    await loadWeeklyStats(); // Обновляем статистику после сброса
  }

  // --- изменение дневной цели ---
  async function updateGoal() {
    if (newGoal < 500 || newGoal > 10000) {
      alert("Цель должна быть от 500 до 10000 мл");
      return;
    }
    
    await fetch(`${API_BASE}/api/webapp/goal`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tg-Init-Data": tg?.initData || "",
      },
      body: JSON.stringify({ goal_ml: newGoal }),
    });
    
    setDailyGoal(newGoal);
    setShowGoalModal(false);
    await loadToday();
    await loadWeeklyStats();
  }

  useEffect(() => {
    loadToday();
    loadWeeklyStats();
  }, []);

  useEffect(() => {
    setNewGoal(dailyGoal);
  }, [dailyGoal]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50 p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <Card className="mb-4">
          <CardHeader className="text-center pb-4">
            <CardTitle className="flex items-center justify-center gap-2">
              <Droplets className="h-6 w-6 text-blue-500" />
              Daily Water Goal
            </CardTitle>
            <div className="flex items-center justify-center mt-2">
              <Badge variant={isGoalReached ? "default" : "secondary"} className="text-center">
                {currentWater}ml / {dailyGoal}ml
              </Badge>
            </div>
            <div className="flex justify-center mt-2">
              <button
                onClick={() => setShowGoalModal(true)}
                className="p-2 rounded-full bg-blue-100 hover:bg-blue-200 transition-all duration-200 hover:scale-110 active:scale-95"
                title="Изменить дневную цель"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="text-blue-600"
                >
                  <path d="M12 20h9" />
                  <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                </svg>
              </button>
            </div>
          </CardHeader>
        </Card>

        {/* Bottle */}
        <div className="flex justify-center mb-4">
          <WaterBottle currentWater={currentWater} totalGoal={dailyGoal} />
        </div>

        {/* Quick Add */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="text-lg">Quick Add</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <Button onClick={() => addWater(defaultGlass)} variant="outline">
                +{defaultGlass}ml
              </Button>
              <Button onClick={() => addWater(500)} variant="outline">
                +500ml
              </Button>
              <Button onClick={() => addWater(750)} variant="outline">
                +750ml
              </Button>
            </div>

            {/* Custom controls */}
            <div className="flex items-center justify-center gap-2">
              <Button onClick={() => addWater(-100)} variant="outline" size="sm">
                <Minus className="h-4 w-4" /> 100ml
              </Button>
              <Button onClick={() => addWater(100)} variant="outline" size="sm">
                <Plus className="h-4 w-4" /> 100ml
              </Button>
              <Button
                onClick={resetWater}
                variant="outline"
                size="sm"
                className="ml-2"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Progress stats */}
        <Card className={`mb-4 ${isGoalReached ? "border-green-200 bg-green-50" : ""}`}>
          <CardContent className="pt-6">
            <div className="text-center space-y-2">
              <div className={`text-2xl font-semibold ${isGoalReached ? "text-green-600" : "text-blue-600"}`}>
                {Math.round(progress)}% Complete
              </div>
              <div className="text-sm text-gray-600">
                {dailyGoal - currentWater > 0
                  ? `${dailyGoal - currentWater}ml remaining`
                  : "Goal achieved! Keep hydrated!"}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
                <div
                  className={`h-2 rounded-full transition-all duration-700 ease-out ${isGoalReached ? "bg-green-500" : "bg-blue-500"}`}
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weekly Statistics */}
        {weeklyStats && (
          <WeeklyStats days={weeklyStats.days} goalMl={weeklyStats.goal_ml} />
        )}

        {/* Goal Modal */}
        {showGoalModal && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-3 z-50 animate-in fade-in duration-200"
            onClick={() => setShowGoalModal(false)}
          >
            <Card 
              className="w-full max-w-64 animate-in zoom-in-95 slide-in-from-bottom-4 duration-300"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader className="relative pb-3">
                <CardTitle className="text-center text-lg">Изменить цель</CardTitle>
                <button
                  onClick={() => setShowGoalModal(false)}
                  className="absolute top-2 right-2 p-1 rounded-full hover:bg-gray-100 transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Новая цель (мл)
                  </label>
                  <input
                    type="number"
                    value={newGoal}
                    onChange={(e) => setNewGoal(parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min="500"
                    max="10000"
                    step="100"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Рекомендуется: 2000-3000 мл
                  </p>
                </div>
                <div className="flex gap-2 pt-1">
                  <Button
                    onClick={() => setShowGoalModal(false)}
                    variant="outline"
                    size="sm"
                    className="flex-1 text-sm"
                  >
                    Отмена
                  </Button>
                  <Button
                    onClick={updateGoal}
                    size="sm"
                    className="flex-1 text-sm"
                  >
                    Сохранить
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}