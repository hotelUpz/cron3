# ==============================================================================
# Path: FSM/models.py
# Role: Модели состояний FSM
# ==============================================================================

from dataclasses import dataclass, field

@dataclass
class PositionState:
    symbol: str
    side: str  # "LONG" или "SHORT"
    
    total_volume: float = 0.0            # суммарный объем позиции
    avg_entry_price: float = 0.0         # Средняя точка входа
    pre_avg_price: float = 0.0           # Цена входа ДО усреднения (для синхронизации)
    initial_entry_price: float = 0.0     # начальная точка входа позиции
    open_time: int = 0                   # время открытия первой сделки (unix ms)
    current_grid_level: str = "0"        # текущий уровень сетки
    next_avg_price: float = None         # кешированная цена ближайшего усреднения
    next_fallback_price: float = None    # кешированная цена страховочного маркета
    
    in_position: bool = False
    in_position_papper: bool = False
    is_finished: bool = False
    pending_avg: bool = False
    pending_rolling_tp: bool = False
    
    grid: dict = field(default_factory=dict)
    tp_map: dict = field(default_factory=dict)
    
    def set_in_position(self, status: bool):
        self.in_position = status
        if status:
            self.in_position_papper = False
            
    def reset(self):
        """Сброс до дефолта: обнуление всех метрик и флагов."""
        self.total_volume = 0.0
        self.avg_entry_price = 0.0
        self.pre_avg_price = 0.0
        self.initial_entry_price = 0.0
        self.open_time = 0
        self.in_position = False
        self.in_position_papper = False
        self.is_finished = False
        self.pending_avg = False
        self.pending_rolling_tp = False
        self.next_avg_price = None
        self.next_fallback_price = None
        self.current_grid_level = "0"
        self.grid.clear()
        self.tp_map.clear()
