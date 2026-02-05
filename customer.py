import random
import time
import json
from datetime import datetime
from collections import defaultdict
import anthropic
import os


class Customer:
    def __init__(self, name, customer_id, last_output, last_bill, feeder_id, latitude, longitude):
        self.name = name
        self.customer_id = customer_id
        self.last_output = last_output
        self.last_bill = last_bill
        self.feeder_id = feeder_id
        self.latitude = latitude
        self.longitude = longitude
        self.fault_history = []


class Engineer:
    def __init__(self, name, engineer_id, specialty, current_latitude, current_longitude):
        self.name = name
        self.engineer_id = engineer_id
        self.specialty = specialty  # 'transformer', 'line', 'meter', 'general'
        self.current_latitude = current_latitude
        self.current_longitude = current_longitude
        self.assigned_faults = []
        self.workload = 0


FEEDERS = (
    "Zone-A / Feeder-1",
    "Zone-A / Feeder-2",
    "Zone-B / Feeder-3",
    "Zone-C / Feeder-4",
    "Zone-D / Feeder-5",
)

# Initialize engineers with specialties and locations
engineers = [
    Engineer("Eng. Ankit", 0, "transformer", 23.8103, 91.2514),
    Engineer("Eng. Riya", 1, "line", 23.8200, 91.2600),
    Engineer("Eng. Suman", 2, "meter", 23.7900, 91.2400),
    Engineer("Eng. Arjun", 3, "general", 23.8300, 91.2700),
    Engineer("Eng. Neha", 4, "line", 23.7800, 91.2300),
]

NUM_CUSTOMERS = 1000  # Reduced for testing
THRESHOLD = 100
INTERVAL = 120

# Generate customers with random locations (around Agartala, Tripura)
customers = [
    Customer(
        name=f"Customer_{i}",
        customer_id=i + 1,
        last_output=random.randint(50, 500),
        last_bill=random.randint(500, 10000),
        feeder_id=random.randrange(len(FEEDERS)),
        latitude=23.8103 + random.uniform(-0.05, 0.05),
        longitude=91.2514 + random.uniform(-0.05, 0.05)
    )
    for i in range(NUM_CUSTOMERS)
]


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate approximate distance between two coordinates in km."""
    # Simplified distance calculation (Haversine approximation)
    import math

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return 6371 * c  # Earth radius in km


def monitor_outputs():
    """Monitor customer outputs and detect anomalies."""
    flagged = []

    for c in customers:
        new_out = random.randint(50, 500)

        if abs(new_out - c.last_output) > THRESHOLD:
            change_percentage = ((new_out - c.last_output) / c.last_output) * 100

            fault_data = {
                'customer_id': c.customer_id,
                'customer_name': c.name,
                'old_output': c.last_output,
                'new_output': new_out,
                'change_percentage': change_percentage,
                'feeder_id': c.feeder_id,
                'feeder_name': FEEDERS[c.feeder_id],
                'latitude': c.latitude,
                'longitude': c.longitude,
                'last_bill': c.last_bill,
                'timestamp': datetime.now().isoformat()
            }

            flagged.append(fault_data)
            c.fault_history.append(fault_data)

        c.last_output = new_out

    return flagged


def analyze_faults_with_ai(faults):
    """Use Claude AI to analyze faults and provide intelligent insights."""
    if not faults:
        return None

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY not found in environment variables")
        print("To enable AI analysis, set your API key:")
        print("export ANTHROPIC_API_KEY='your-api-key-here'  # Linux/Mac")
        print("set ANTHROPIC_API_KEY=your-api-key-here  # Windows CMD")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Prepare fault summary for AI
        fault_summary = {
            'total_faults': len(faults),
            'feeders_affected': list(set(f['feeder_name'] for f in faults)),
            'fault_samples': faults[:20],  # Send first 20 for analysis
            'available_engineers': [
                {
                    'name': eng.name,
                    'specialty': eng.specialty,
                    'current_workload': eng.workload,
                    'location': {'lat': eng.current_latitude, 'lng': eng.current_longitude}
                }
                for eng in engineers
            ]
        }

        prompt = f"""You are an AI assistant for an electricity distribution monitoring system. Analyze the following fault data and provide:

1. **Failure Type Classification**: For each fault, classify the likely cause (transformer failure, line break, meter malfunction, voltage fluctuation, etc.)

2. **Smart Engineer Assignment**: Assign the most suitable engineer based on:
   - Engineer specialty matching the fault type
   - Current workload
   - Proximity to fault location
   - Urgency of the fault

3. **Route Optimization**: For multiple faults assigned to the same engineer, suggest an optimal route sequence

4. **Pattern Detection**: Identify any patterns (e.g., multiple faults in same feeder, time-based patterns, geographical clusters)

5. **Predictive Insights**: Based on the data, predict potential cascading failures or areas at risk

Fault Data:
{json.dumps(fault_summary, indent=2)}

Provide your analysis in JSON format with the following structure:
{{
  "failure_classifications": [
    {{"customer_id": <id>, "fault_type": "<type>", "severity": "<low/medium/high>", "reason": "<explanation>"}}
  ],
  "engineer_assignments": [
    {{"customer_id": <id>, "assigned_engineer": "<name>", "reason": "<why this engineer>", "estimated_travel_time": "<minutes>"}}
  ],
  "optimized_routes": [
    {{"engineer": "<name>", "route_sequence": [<customer_ids>], "total_distance": "<km>", "estimated_time": "<hours>"}}
  ],
  "patterns_detected": ["<pattern 1>", "<pattern 2>"],
  "predictions": ["<prediction 1>", "<prediction 2>"],
  "recommendations": ["<recommendation 1>", "<recommendation 2>"]
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse AI response
        response_text = message.content[0].text

        # Extract JSON from response (in case there's extra text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            ai_analysis = json.loads(response_text[json_start:json_end])
            return ai_analysis
        else:
            print("\n⚠️  Could not parse AI response as JSON")
            return None

    except Exception as e:
        print(f"\n⚠️  AI Analysis Error: {e}")
        return None


def assign_engineers_smartly(faults, ai_analysis):
    """Assign engineers based on AI recommendations or fallback to basic logic."""
    assignments = []

    if ai_analysis and 'engineer_assignments' in ai_analysis:
        # Use AI recommendations
        for assignment in ai_analysis['engineer_assignments']:
            fault = next((f for f in faults if f['customer_id'] == assignment['customer_id']), None)
            if fault:
                engineer = next((e for e in engineers if e.name == assignment['assigned_engineer']), None)
                if engineer:
                    assignments.append({
                        **fault,
                        'assigned_engineer': engineer.name,
                        'engineer_specialty': engineer.specialty,
                        'assignment_reason': assignment.get('reason', 'AI recommendation'),
                        'estimated_travel_time': assignment.get('estimated_travel_time', 'N/A'),
                        'ai_assigned': True
                    })
                    engineer.workload += 1
    else:
        # Fallback: Basic assignment by distance and workload
        for fault in faults:
            best_engineer = None
            min_score = float('inf')

            for eng in engineers:
                distance = calculate_distance(
                    fault['latitude'], fault['longitude'],
                    eng.current_latitude, eng.current_longitude
                )
                # Score = distance + workload penalty
                score = distance + (eng.workload * 2)

                if score < min_score:
                    min_score = score
                    best_engineer = eng

            if best_engineer:
                assignments.append({
                    **fault,
                    'assigned_engineer': best_engineer.name,
                    'engineer_specialty': best_engineer.specialty,
                    'distance_km': round(min_score, 2),
                    'assignment_reason': 'Distance + workload optimization',
                    'ai_assigned': False
                })
                best_engineer.workload += 1

    return assignments


def display_ai_insights(ai_analysis):
    """Display AI-generated insights in a readable format."""
    if not ai_analysis:
        return

    print("\n" + "=" * 80)
    print("🤖 AI-POWERED INSIGHTS")
    print("=" * 80)

    # Failure Classifications
    if 'failure_classifications' in ai_analysis:
        print("\n📋 FAILURE CLASSIFICATIONS:")
        for fc in ai_analysis['failure_classifications'][:10]:
            print(f"  • Customer {fc.get('customer_id')}: {fc.get('fault_type')} "
                  f"[{fc.get('severity', 'unknown').upper()}]")
            print(f"    Reason: {fc.get('reason', 'N/A')}")

    # Patterns Detected
    if 'patterns_detected' in ai_analysis and ai_analysis['patterns_detected']:
        print("\n🔍 PATTERNS DETECTED:")
        for pattern in ai_analysis['patterns_detected']:
            print(f"  • {pattern}")

    # Predictions
    if 'predictions' in ai_analysis and ai_analysis['predictions']:
        print("\n🔮 PREDICTIVE INSIGHTS:")
        for prediction in ai_analysis['predictions']:
            print(f"  • {prediction}")

    # Recommendations
    if 'recommendations' in ai_analysis and ai_analysis['recommendations']:
        print("\n💡 RECOMMENDATIONS:")
        for rec in ai_analysis['recommendations']:
            print(f"  • {rec}")

    # Optimized Routes
    if 'optimized_routes' in ai_analysis:
        print("\n🗺️  OPTIMIZED ROUTES:")
        for route in ai_analysis['optimized_routes']:
            print(f"  • {route.get('engineer')}: {len(route.get('route_sequence', []))} stops")
            print(f"    Total Distance: {route.get('total_distance', 'N/A')}, "
                  f"Est. Time: {route.get('estimated_time', 'N/A')}")

    print("\n" + "=" * 80)


def log_faults_and_assignments(assignments, ai_analysis, cycle_count):
    """Log detected faults and AI analysis to file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_file = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Always create a JSON file for each cycle
    cycle_data = {
        "cycle_number": cycle_count,
        "timestamp": timestamp,
        "total_faults": len(assignments) if assignments else 0,
        "faults": [],
        "summary": {
            "feeders": {},
            "engineers": {}
        },
        "ai_analysis": ai_analysis if ai_analysis else None
    }

    # Add fault details
    if assignments:
        for assignment in assignments:
            fault_entry = {
                "customer_id": assignment['customer_id'],
                "customer_name": assignment['customer_name'],
                "feeder_id": assignment['feeder_id'],
                "feeder_name": assignment['feeder_name'],
                "old_output": assignment['old_output'],
                "new_output": assignment['new_output'],
                "change_percentage": round(assignment['change_percentage'], 2),
                "latitude": assignment['latitude'],
                "longitude": assignment['longitude'],
                "assigned_engineer": assignment['assigned_engineer'],
                "engineer_specialty": assignment['engineer_specialty'],
                "assignment_reason": assignment.get('assignment_reason', 'N/A'),
                "ai_assigned": assignment.get('ai_assigned', False)
            }
            cycle_data["faults"].append(fault_entry)

        # Generate summary statistics
        feeder_counts = defaultdict(int)
        engineer_counts = defaultdict(int)

        for assignment in assignments:
            feeder_counts[assignment['feeder_name']] += 1
            engineer_counts[assignment['assigned_engineer']] += 1

        cycle_data["summary"]["feeders"] = dict(feeder_counts)
        cycle_data["summary"]["engineers"] = dict(engineer_counts)

    # Save complete cycle data to JSON
    json_filename = f"cycle_{cycle_count:04d}_{timestamp_file}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(cycle_data, f, indent=2)

    print(f"\n💾 Data saved to: {json_filename}")

    # Also append to text log
    if assignments:
        with open("fault_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Cycle: {cycle_count}\n")
            f.write(f"Total Faults Detected: {len(assignments)}\n")
            f.write(f"{'-' * 80}\n")

            for assignment in assignments:
                f.write(
                    f"Customer ID: {assignment['customer_id']:6d} | "
                    f"Feeder: {assignment['feeder_id']} | "
                    f"Output: {assignment['old_output']:3d} -> {assignment['new_output']:3d} | "
                    f"Location: {assignment['feeder_name']:20s} | "
                    f"Engineer: {assignment['assigned_engineer']} ({assignment['engineer_specialty']})\n"
                )
                if assignment.get('ai_assigned'):
                    f.write(f"  AI Reason: {assignment.get('assignment_reason', 'N/A')}\n")


def generate_summary(assignments):
    """Generate summary statistics."""
    if not assignments:
        return

    feeder_counts = defaultdict(int)
    engineer_counts = defaultdict(int)

    for assignment in assignments:
        feeder_counts[assignment['feeder_id']] += 1
        engineer_counts[assignment['assigned_engineer']] += 1

    print("\n📊 FAULT SUMMARY:")
    print(f"{'Feeder':<25} {'Faults':>10}")
    print("-" * 37)
    for fid in sorted(feeder_counts.keys()):
        print(f"{FEEDERS[fid]:<25} {feeder_counts[fid]:>10}")

    print(f"\n{'Engineer':<25} {'Assigned':>10}")
    print("-" * 37)
    for eng in sorted(engineer_counts.keys()):
        print(f"{eng:<25} {engineer_counts[eng]:>10}")


def run_monitoring_cycle(cycle_count):
    """Run a single monitoring cycle with AI analysis."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'=' * 80}")
    print(f"[Cycle {cycle_count}] {timestamp}")
    print(f"{'=' * 80}")

    # Reset engineer workloads
    for eng in engineers:
        eng.workload = 0
        eng.assigned_faults = []

    # Monitor outputs
    faults = monitor_outputs()

    if faults:
        print(f"\n⚠️  {len(faults)} faults detected")

        # AI Analysis
        print("\n🤖 Running AI analysis...")
        ai_analysis = analyze_faults_with_ai(faults)

        # Smart engineer assignment
        assignments = assign_engineers_smartly(faults, ai_analysis)

        # Display assignments
        print(f"\n{'=' * 80}")
        print("📋 FAULT ASSIGNMENTS")
        print(f"{'=' * 80}\n")

        for assignment in assignments[:20]:  # Show first 20
            ai_indicator = "🤖" if assignment.get('ai_assigned') else "📍"
            print(
                f"{ai_indicator} ID {assignment['customer_id']:6d} | "
                f"Feeder {assignment['feeder_id']} | "
                f"{assignment['old_output']:3d} -> {assignment['new_output']:3d} | "
                f"{assignment['feeder_name']:20s} | "
                f"→ {assignment['assigned_engineer']} ({assignment['engineer_specialty']})"
            )
            if assignment.get('ai_assigned'):
                print(f"   Reason: {assignment.get('assignment_reason', 'N/A')}")

        if len(assignments) > 20:
            print(f"\n... and {len(assignments) - 20} more assignments")

        # Display AI insights
        display_ai_insights(ai_analysis)

        # Generate summary
        generate_summary(assignments)

        # Log everything (now includes cycle_count parameter)
        log_faults_and_assignments(assignments, ai_analysis, cycle_count)

    else:
        print("\n✅ No anomalies detected")
        # Still create JSON file even with no faults
        log_faults_and_assignments([], None, cycle_count)

    print("\n" + "-" * 80)


# Main execution
print("=" * 80)
print("⚡ SMART CUSTOMER OUTPUT MONITORING SYSTEM")
print("=" * 80)
print(f"\nMonitoring {NUM_CUSTOMERS:,} customers across {len(FEEDERS)} feeders")
print(f"Threshold: {THRESHOLD} units | Interval: {INTERVAL}s ({INTERVAL // 60} minutes)")
print(f"\nAI Features:")
print("  • Smart Engineer Assignment")
print("  • Route Optimization")
print("  • Failure Type Classification")
print("  • Pattern Detection")
print("  • Predictive Analytics")
print("\n" + "=" * 80)

# Check for API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("\n⚠️  WARNING: ANTHROPIC_API_KEY not found!")
    print("AI features will be disabled. To enable:")
    print("  1. Get an API key from https://console.anthropic.com/")
    print("  2. Set environment variable:")
    print("     export ANTHROPIC_API_KEY='your-key'  # Linux/Mac")
    print("     set ANTHROPIC_API_KEY=your-key      # Windows CMD")
    print("\nRunning in basic mode...\n")

cycle_count = 0

while True:
    cycle_count += 1

    # Run monitoring cycle
    run_monitoring_cycle(cycle_count)

    # Wait for the specified interval (2 minutes)
    print(f"\n⏳ Waiting {INTERVAL}s until next cycle...")
    print(f"Next cycle at: {datetime.fromtimestamp(time.time() + INTERVAL).strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(INTERVAL)