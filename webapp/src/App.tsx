import { useState, useEffect } from "react";
import { WaterBottle } from "./components/WaterBottle";
import { WeeklyStats } from "./components/WeeklyStats";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Droplets, Plus, Minus, RotateCcw } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE || "";
const tg = (window as any).Telegram?.WebApp;

export default function App() {
  const [currentWater, setCurrentWater] = useState(0);
  const [dailyGoal, setDailyGoal] = useState(2000);
  const [defaultGlass, setDefaultGlass] = useState(250);
  const [progress, setProgress] = useState(0);
  const [isGoalReached, setIsGoalReached] = useState(false);
  const [weeklyStats, setWeeklyStats] = useState<{days: Array<{date: string, ml: number}>, goal_ml: number} | null>(null);

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

  useEffect(() => {
    loadToday();
    loadWeeklyStats();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50 p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <Card className="mb-6">
          <CardHeader className="text-center pb-4">
            <CardTitle className="flex items-center justify-center gap-2">
              <Droplets className="h-6 w-6 text-blue-500" />
              Daily Water Goal
            </CardTitle>
            <div className="flex items-center justify-center gap-4 mt-2">
              <Badge variant={isGoalReached ? "default" : "secondary"}>
                {currentWater}ml / {dailyGoal}ml
              </Badge>
              {isGoalReached && <div className="text-2xl">🎉</div>}
            </div>
          </CardHeader>
        </Card>

        {/* Bottle */}
        <div className="flex justify-center mb-6">
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
        <Card>
          <CardContent className="pt-6">
            <div className="text-center space-y-2">
              <div className="text-2xl font-semibold text-blue-600">
                {Math.round(progress)}% Complete
              </div>
              <div className="text-sm text-gray-600">
                {dailyGoal - currentWater > 0
                  ? `${dailyGoal - currentWater}ml remaining`
                  : "Goal achieved! Keep hydrated!"}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Achievement message */}
        {isGoalReached && (
          <div className="mt-4 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-6">
                <div className="text-green-800">
                  <div className="text-2xl mb-2">🏆</div>
                  <h3 className="font-semibold">Congratulations!</h3>
                  <p className="text-sm">
                    You've reached your daily water goal!
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Weekly Statistics */}
        {weeklyStats && (
          <WeeklyStats days={weeklyStats.days} goalMl={weeklyStats.goal_ml} />
        )}
      </div>
    </div>
  );
}