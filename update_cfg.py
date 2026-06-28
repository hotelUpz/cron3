import json
from pathlib import Path

# User's provided backup payload
payload = """
{
    "_base.json": {
        "LONG": {
            "enable": true,
            "invest_size": 2000,
            "leverage": 10,
            "margin_type": "CROSSED",
            "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
            "grid": {
                "0": { "indent": 0, "volume": 12.96 },
                "1": { "indent": -4.0, "volume": 14.26 },
                "2": { "indent": -8.0, "volume": 15.68 },
                "3": { "indent": -13.0, "volume": 17.25 },
                "4": { "indent": -19.0, "volume": 18.98 },
                "5": { "indent": -26.0, "volume": 20.87 }
            },
            "tp_map": {
                "0": { "indent": 0.6, "fallback_indent": 1.0 },
                "1": { "indent": 0.7, "fallback_indent": 1.6 },
                "2": { "indent": 1.0, "fallback_indent": 2.3 },
                "3": { "indent": 1.4, "fallback_indent": 3.0 },
                "4": { "indent": 1.9, "fallback_indent": 3.6 },
                "5": { "indent": 1.9, "fallback_indent": 3.6 }
            }
        },
        "SHORT": {
            "enable": true,
            "invest_size": 2000,
            "leverage": 10,
            "margin_type": "CROSSED",
            "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
            "grid": {
                "0": { "indent": 0, "volume": 12.96 },
                "1": { "indent": -4.0, "volume": 14.26 },
                "2": { "indent": -8.0, "volume": 15.68 },
                "3": { "indent": -13.0, "volume": 17.25 },
                "4": { "indent": -19.0, "volume": 18.98 },
                "5": { "indent": -26.0, "volume": 20.87 }
            },
            "tp_map": {
                "0": { "indent": 0.6, "fallback_indent": 1.0 },
                "1": { "indent": 0.7, "fallback_indent": 1.6 },
                "2": { "indent": 1.0, "fallback_indent": 2.3 },
                "3": { "indent": 1.4, "fallback_indent": 3.0 },
                "4": { "indent": 1.9, "fallback_indent": 3.6 },
                "5": { "indent": 1.9, "fallback_indent": 3.6 }
            }
        }
    },
    "runtime": {
        "stableusdt.json": {
            "LONG": {
                "enable": true,
                "invest_size": 2000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 0.0379886753513 },
                    "1": { "indent": -4.0, "volume": 14.26, "is_active": false, "price": 0.03647 },
                    "2": { "indent": -8.0, "volume": 15.68, "is_active": false, "price": 0.03495 },
                    "3": { "indent": -13.0, "volume": 17.25, "is_active": false, "price": 0.03305 },
                    "4": { "indent": -19.0, "volume": 18.98, "is_active": false, "price": 0.03077 },
                    "5": { "indent": -26.0, "volume": 20.87, "is_active": false, "price": 0.02811 }
                },
                "tp_map": {
                    "0": { "indent": 0.5, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "total_volume": 6832.0,
                "avg_entry_price": 0.0379886753513,
                "pre_avg_price": 0.0,
                "initial_entry_price": 0.0379886753513,
                "open_time": 1782644400066,
                "next_avg_price": 0.03647,
                "fallback_price": 0.03837,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false
            },
            "SHORT": {
                "enable": true,
                "invest_size": 2000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 0.0370416680961 },
                    "1": { "indent": -4.0, "volume": 14.26, "is_active": false, "price": 0.03852 },
                    "2": { "indent": -8.0, "volume": 15.68, "is_active": false, "price": 0.04001 },
                    "3": { "indent": -13.0, "volume": 17.25, "is_active": false, "price": 0.04186 },
                    "4": { "indent": -19.0, "volume": 18.98, "is_active": false, "price": 0.04408 },
                    "5": { "indent": -26.0, "volume": 20.87, "is_active": false, "price": 0.04667 }
                },
                "tp_map": {
                    "0": { "indent": 0.5, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "total_volume": -6996.0,
                "avg_entry_price": 0.0370416680961,
                "pre_avg_price": 0.0,
                "initial_entry_price": 0.0370416680961,
                "open_time": 1782640818472,
                "next_avg_price": 0.03852,
                "fallback_price": 0.03667,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false
            }
        },
        "jupusdt.json": {
            "LONG": {
                "enable": true,
                "invest_size": 2000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 0.2209 },
                    "1": { "indent": -6.1, "volume": 14.26, "price": 0.2074, "is_active": false },
                    "2": { "indent": -12.3, "volume": 15.68, "price": 0.1937, "is_active": false },
                    "3": { "indent": -19.0, "volume": 17.25, "price": 0.1789, "is_active": false },
                    "4": { "indent": -29.0, "volume": 18.98, "price": 0.1568, "is_active": false },
                    "5": { "indent": -40.0, "volume": 20.87, "price": 0.1325, "is_active": false }
                },
                "tp_map": {
                    "0": { "indent": 0.6, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "next_avg_price": 0.2074,
                "total_volume": 1173.0,
                "avg_entry_price": 0.2209,
                "pre_avg_price": 0.0,
                "initial_entry_price": 0.2209,
                "open_time": 1782600000319,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false,
                "fallback_price": 0.2231
            },
            "SHORT": {
                "enable": true,
                "invest_size": 2000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 0.2139 },
                    "1": { "indent": -6.1, "volume": 14.26, "price": 0.2269, "is_active": false },
                    "2": { "indent": -12.3, "volume": 15.68, "price": 0.2402, "is_active": false },
                    "3": { "indent": -19.0, "volume": 17.25, "price": 0.2545, "is_active": false },
                    "4": { "indent": -29.0, "volume": 18.98, "price": 0.2759, "is_active": false },
                    "5": { "indent": -40.0, "volume": 20.87, "price": 0.2995, "is_active": false }
                },
                "tp_map": {
                    "0": { "indent": 0.6, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "next_avg_price": 0.2269,
                "total_volume": -1211.0,
                "avg_entry_price": 0.2139,
                "pre_avg_price": 0.0,
                "initial_entry_price": 0.2139,
                "open_time": 1782627600172,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false,
                "fallback_price": 0.2118
            }
        },
        "solusdt.json": {
            "LONG": {
                "enable": true,
                "invest_size": 3000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 73.12 },
                    "1": { "indent": -5.0, "volume": 14.26, "is_active": false, "price": 69.46 },
                    "2": { "indent": -9.0, "volume": 15.68, "is_active": false, "price": 66.54 },
                    "3": { "indent": -14.0, "volume": 17.25, "is_active": false, "price": 62.88 },
                    "4": { "indent": -21.0, "volume": 18.98, "is_active": false, "price": 57.76 },
                    "5": { "indent": -30.0, "volume": 20.87, "is_active": false, "price": 51.18 }
                },
                "tp_map": {
                    "0": { "indent": 0.5, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "total_volume": 3.54,
                "avg_entry_price": 73.12,
                "pre_avg_price": 0.0,
                "initial_entry_price": 73.12,
                "open_time": 1782573057706,
                "next_avg_price": 69.46,
                "fallback_price": 73.85,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false
            },
            "SHORT": {
                "enable": true,
                "invest_size": 3000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 70.2 },
                    "1": { "indent": -5.0, "volume": 14.26, "is_active": false, "price": 73.71 },
                    "2": { "indent": -9.0, "volume": 15.68, "is_active": false, "price": 76.52 },
                    "3": { "indent": -14.0, "volume": 17.25, "is_active": false, "price": 80.03 },
                    "4": { "indent": -21.0, "volume": 18.98, "is_active": false, "price": 84.94 },
                    "5": { "indent": -30.0, "volume": 20.87, "is_active": false, "price": 91.26 }
                },
                "tp_map": {
                    "0": { "indent": 0.5, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "total_volume": -5.54,
                "avg_entry_price": 70.2,
                "pre_avg_price": 0.0,
                "initial_entry_price": 70.2,
                "open_time": 1782624600117,
                "next_avg_price": 73.71,
                "fallback_price": 69.5,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false
            }
        },
        "dashusdt.json": {
            "LONG": {
                "enable": true,
                "invest_size": 3000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 34.83 },
                    "1": { "indent": -5.0, "volume": 14.26, "is_active": true, "price": 33.09 },
                    "2": { "indent": -9.0, "volume": 15.68, "is_active": false, "price": 31.7 },
                    "3": { "indent": -14.0, "volume": 17.25, "is_active": false, "price": 29.95 },
                    "4": { "indent": -21.0, "volume": 18.98, "is_active": false, "price": 27.52 },
                    "5": { "indent": -30.0, "volume": 20.87, "is_active": false, "price": 24.38 }
                },
                "tp_map": {
                    "0": { "indent": 0.6, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": true },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "total_volume": 16.063,
                "avg_entry_price": 33.89635995766,
                "pre_avg_price": 34.83,
                "initial_entry_price": 34.83,
                "open_time": 1782505501744,
                "next_avg_price": 31.7,
                "fallback_price": 34.44,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false
            },
            "SHORT": {
                "enable": true,
                "invest_size": 3000,
                "leverage": 10,
                "margin_type": "CROSSED",
                "_comment_margin_type": "Valid values: CROSSED | ISOLATED",
                "grid": {
                    "0": { "indent": 0, "volume": 12.96, "is_active": true, "price": 32.1203662065 },
                    "1": { "indent": -5.0, "volume": 14.26, "is_active": false, "price": 33.73 },
                    "2": { "indent": -9.0, "volume": 15.68, "is_active": false, "price": 35.01 },
                    "3": { "indent": -14.0, "volume": 17.25, "is_active": false, "price": 36.62 },
                    "4": { "indent": -21.0, "volume": 18.98, "is_active": false, "price": 38.87 },
                    "5": { "indent": -30.0, "volume": 20.87, "is_active": false, "price": 41.76 }
                },
                "tp_map": {
                    "0": { "indent": 0.6, "fallback_indent": 1.0, "is_active": true },
                    "1": { "indent": 0.7, "fallback_indent": 1.6, "is_active": false },
                    "2": { "indent": 1.0, "fallback_indent": 2.3, "is_active": false },
                    "3": { "indent": 1.4, "fallback_indent": 3.0, "is_active": false },
                    "4": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false },
                    "5": { "indent": 1.9, "fallback_indent": 3.6, "is_active": false }
                },
                "total_volume": -12.097,
                "avg_entry_price": 32.1203662065,
                "pre_avg_price": 0.0,
                "initial_entry_price": 32.1203662065,
                "open_time": 1782649200057,
                "next_avg_price": 33.73,
                "fallback_price": 31.8,
                "in_position": true,
                "in_position_papper": false,
                "is_finished": false,
                "pending_avg": false,
                "pending_rolling_tp": false
            }
        }
    }
}
"""

def process_file_data(data):
    if "LONG" in data and "grid" in data["LONG"]:
        for key in data["LONG"]["grid"]:
            data["LONG"]["grid"][key]["super_indent"] = None
    if "SHORT" in data and "grid" in data["SHORT"]:
        for key in data["SHORT"]["grid"]:
            data["SHORT"]["grid"][key]["super_indent"] = None
    return data

def main():
    parsed = json.loads(payload)
    
    # Update _base.json
    base_file = Path("CFG/_base.json")
    if base_file.exists():
        with open(base_file, "r") as f:
            base_data = json.load(f)
    else:
        base_data = {}
        
    # Apply _base.json payload
    base_data["LONG"] = process_file_data({"LONG": parsed["_base.json"]["LONG"]})["LONG"]
    base_data["SHORT"] = process_file_data({"SHORT": parsed["_base.json"]["SHORT"]})["SHORT"]
    
    # Ensure super_grid is present and disabled
    if "super_grid" not in base_data:
        base_data["super_grid"] = {}
    base_data["super_grid"]["enabled"] = False
    
    with open(base_file, "w") as f:
        json.dump(base_data, f, indent=4)
        
    print("Updated CFG/_base.json")
    
    # Update runtime files
    for filename, runtime_data in parsed["runtime"].items():
        filepath = Path("CFG/runtime") / filename
        processed_data = process_file_data(runtime_data)
        
        with open(filepath, "w") as f:
            json.dump(processed_data, f, indent=4)
        print(f"Updated {filepath}")

if __name__ == "__main__":
    main()
