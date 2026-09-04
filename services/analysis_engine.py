from typing import Dict, Any, Optional

class AgriculturalDecisionEngine:
    """Evaluates crop requirements against rover sensor telemetry to compute
    environmental suitability ratings, irrigation decisions, and agronomic guidance.
    """

    def evaluate_metric(self, current: Optional[float], min_val: float, max_val: float) -> str:
        """Categorizes sensor reading into OPTIMAL, GOOD, MODERATE, NEEDS ATTENTION, UNSUITABLE, or UNKNOWN."""
        if current is None:
            return "UNKNOWN"

        margin = (max_val - min_val) * 0.15
        
        if min_val <= current <= max_val:
            mid = (min_val + max_val) / 2.0
            if abs(current - mid) <= margin:
                return "OPTIMAL"
            return "GOOD"
        elif (min_val - margin) <= current < min_val or max_val < current <= (max_val + margin):
            return "MODERATE"
        elif (min_val - 2 * margin) <= current < (min_val - margin) or (max_val + margin) < current <= (max_val + 2 * margin):
            return "NEEDS ATTENTION"
        else:
            return "UNSUITABLE"

    def analyze(self, vision_result: Dict[str, Any], crop_profile: Optional[Dict[str, Any]], sensor_data: Dict[str, Optional[float]]) -> Dict[str, Any]:
        """Combines AI vision output, crop knowledge database, and live sensor readings."""
        
        identified_item = vision_result.get("identified_item") or vision_result.get("crop_name", "Unknown")
        scientific_name = vision_result.get("scientific_name", "")
        category = vision_result.get("category", "unknown/non-agricultural object")
        confidence = vision_result.get("confidence", 0.0)
        candidates = vision_result.get("candidates", [])
        
        visible_condition = vision_result.get("visible_condition") or vision_result.get("visible_condition_status", "Unknown")
        visible_symptoms = vision_result.get("visible_damage_or_symptoms") or vision_result.get("visible_abnormalities", "None detected")
        explanation = vision_result.get("explanation", "")
        ai_recs = vision_result.get("recommendations", "")

        has_sensor_data = any(v is not None for v in sensor_data.values())

        moisture = sensor_data.get("soil_moisture")
        temp = sensor_data.get("temperature")
        humidity = sensor_data.get("humidity")
        ph = sensor_data.get("ph")

        if crop_profile:
            pref_ph_min = crop_profile.get("preferred_ph_min", 6.0)
            pref_ph_max = crop_profile.get("preferred_ph_max", 7.5)
            t_min = crop_profile.get("temp_min_c", 18)
            t_max = crop_profile.get("temp_max_c", 30)
            h_min = crop_profile.get("humidity_min_pct", 50)
            h_max = crop_profile.get("humidity_max_pct", 75)
            m_min = crop_profile.get("moisture_min_pct", 40)
            m_max = crop_profile.get("moisture_max_pct", 70)

            temp_fit = self.evaluate_metric(temp, t_min, t_max) if temp is not None else "UNKNOWN"
            humidity_fit = self.evaluate_metric(humidity, h_min, h_max) if humidity is not None else "UNKNOWN"
            moisture_fit = self.evaluate_metric(moisture, m_min, m_max) if moisture is not None else "UNKNOWN"
            ph_fit = self.evaluate_metric(ph, pref_ph_min, pref_ph_max) if ph is not None else "UNKNOWN"

            soil_text = crop_profile.get("suitable_soil", "Well-drained agricultural soil.")
            ph_text = f"{pref_ph_min} - {pref_ph_max}"
            water_need_text = crop_profile.get("water_requirement", "Moderate water requirement.")
            usefulness_text = crop_profile.get("uses", "Agricultural produce.")
            irrigation_profile_guidance = crop_profile.get("irrigation_guidance", "")
            growth_stages = crop_profile.get("growth_stages", [])
            common_problems = crop_profile.get("common_problems", [])

            # Smart Irrigation Logic
            if moisture is None:
                irrigation_status = "NO LIVE SENSOR DATA"
                irrigation_rec = "No live sensor data available to evaluate current irrigation needs."
            elif moisture < m_min:
                irrigation_status = "IRRIGATION REQUIRED"
                irrigation_rec = f"Soil moisture ({moisture:.1f}%) is below ideal range ({m_min}-{m_max}%) for {identified_item}. Controlled irrigation recommended."
            elif moisture > m_max:
                irrigation_status = "EXCESS MOISTURE"
                irrigation_rec = f"Soil moisture ({moisture:.1f}%) exceeds optimal upper bound ({m_min}-{m_max}%) for {identified_item}. Ensure adequate drainage."
            else:
                irrigation_status = "OPTIMAL MOISTURE"
                irrigation_rec = f"Soil moisture ({moisture:.1f}%) is within optimal range for {identified_item} under ambient temperature ({temp if temp else 'N/A'}°C) and humidity ({humidity if humidity else 'N/A'}%). No immediate irrigation indicated."

            if irrigation_profile_guidance and moisture is not None:
                irrigation_rec += f" Crop Guidance: {irrigation_profile_guidance}"

            # Agronomic Advice Assembly
            rec_blocks = []
            if visible_condition in ["Poor", "Damaged"]:
                rec_blocks.append(f"⚠️ Visual Condition Alert ({visible_condition}): {visible_symptoms}. Isolate affected samples and check for fungal rot or pest activity.")
            elif visible_condition in ["Fair"]:
                rec_blocks.append(f"ℹ️ Visual Condition: Fair. Monitor crop closely for worsening symptoms.")
            else:
                rec_blocks.append(f"✅ Visual Condition: Healthy. Sample shows clean physical characteristics.")

            if ai_recs:
                rec_blocks.append(f"💡 AI Vision Insight: {ai_recs}")

            if has_sensor_data:
                if moisture_fit in ["NEEDS ATTENTION", "UNSUITABLE"]:
                    rec_blocks.append(f"💧 Moisture Action: Adjust irrigation to reach target {m_min}-{m_max}% moisture range.")
                if ph_fit in ["NEEDS ATTENTION", "UNSUITABLE"]:
                    rec_blocks.append(f"🧪 Soil pH Action: Soil pH ({ph}) is outside ideal bounds ({pref_ph_min}-{pref_ph_max}).")
            else:
                rec_blocks.append(f"📡 Sensor Status: No live rover sensor data connected. Environmental suitability calculated from visual profile.")

            rec_blocks.append(f"🌱 Growth Conditions: {crop_profile.get('growth_conditions', '')}")

            overall_recommendation = "\n\n".join(rec_blocks)

        else:
            temp_fit = "UNKNOWN"
            humidity_fit = "UNKNOWN"
            moisture_fit = "UNKNOWN"
            ph_fit = "UNKNOWN"
            soil_text = "Unknown / Crop profile not in database"
            ph_text = "—"
            water_need_text = "—"
            usefulness_text = "—"
            irrigation_status = "NO CROP DATA"
            irrigation_rec = "Cannot determine irrigation requirements without specific crop identification."
            growth_stages = []
            common_problems = []

            if identified_item in ["Not a crop/seed or unable to identify", "Unknown"]:
                overall_recommendation = f"The uploaded image could not be reliably identified as an agricultural crop, seed, or plant sample.\n\nObservation: {explanation}\n\nPlease upload a clear photograph of a crop, leaf, fruit, or seed under good lighting."
            else:
                overall_recommendation = f"Identified sample as '{identified_item}', but detailed profile is not available in the database.\n\nObservation: {explanation}"

        return {
            "identified_item": identified_item,
            "crop_name": identified_item,
            "scientific_name": scientific_name,
            "category": category,
            "confidence": confidence,
            "candidates": candidates,
            
            "visible_condition": visible_condition,
            "visible_damage_or_symptoms": visible_symptoms,
            "explanation": explanation,
            
            "environment": {
                "temperature": {
                    "rating": temp_fit,
                    "current": temp if temp is not None else "No live sensor data",
                    "ideal": f"{crop_profile.get('temp_min_c', '—')}-{crop_profile.get('temp_max_c', '—')} °C" if crop_profile else "—"
                },
                "humidity": {
                    "rating": humidity_fit,
                    "current": humidity if humidity is not None else "No live sensor data",
                    "ideal": f"{crop_profile.get('humidity_min_pct', '—')}-{crop_profile.get('humidity_max_pct', '—')} %" if crop_profile else "—"
                },
                "soil_moisture": {
                    "rating": moisture_fit,
                    "current": moisture if moisture is not None else "No live sensor data",
                    "ideal": f"{crop_profile.get('moisture_min_pct', '—')}-{crop_profile.get('moisture_max_pct', '—')} %" if crop_profile else "—"
                },
                "ph": {
                    "rating": ph_fit,
                    "current": ph if ph is not None else "No live sensor data",
                    "ideal": f"{crop_profile.get('preferred_ph_min', '—')}-{crop_profile.get('preferred_ph_max', '—')}" if crop_profile else "—"
                }
            },

            "crop_details": {
                "suitable_soil": soil_text,
                "preferred_ph": ph_text,
                "temperature_range": f"{crop_profile.get('temp_min_c', '—')}-{crop_profile.get('temp_max_c', '—')} °C" if crop_profile else "—",
                "humidity_guidance": f"{crop_profile.get('humidity_min_pct', '—')}-{crop_profile.get('humidity_max_pct', '—')} %" if crop_profile else "—",
                "water_need": water_need_text,
                "usefulness": usefulness_text
            },

            "irrigation": {
                "status": irrigation_status,
                "recommendation": irrigation_rec
            },

            "growth_guidance": growth_stages,
            "common_problems": common_problems,
            "recommendation": overall_recommendation,
            "has_sensor_data": has_sensor_data
        }
