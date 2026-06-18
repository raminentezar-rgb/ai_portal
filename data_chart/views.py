from accounts.decorators import check_credits, deduct_credit
import json
import g4f
import concurrent.futures
from django.shortcuts import render

def parse_chart_json(json_str):
    try:
        json_str = json_str.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        elif json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        return json.loads(json_str.strip())
    except Exception as e:
        return None

@check_credits
def data_chart(request):
    if request.method == 'POST':
        source_text = request.POST.get('source_text', '').strip()
        chart_type = request.POST.get('chart_type', 'bar')
        
        if not source_text or len(source_text) < 10:
            return render(request, 'data_chart/data_chart.html', {'error': 'Not enough text provided.'})
            
        prompt = f"""
Analyze the following text which contains some statistical or numeric data.
Extract the data points into a valid JSON array of labels and their corresponding numeric values.

The output MUST be valid JSON matching this exact structure:
{{
  "chart_title": "A suitable title for the chart",
  "data_label": "What the values represent (e.g., 'Sales in USD', 'Population')",
  "labels": ["Label 1", "Label 2", "Label 3"],
  "values": [10.5, 20.0, 30.2]
}}
Ensure the lengths of 'labels' and 'values' arrays are strictly equal.
Return ONLY the raw JSON string.

Text to analyze:
{source_text[:5000]}
"""

        def fetch_g4f():
            return g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=[{"role": "user", "content": prompt}]
            )

        chart_data = None
        for attempt in range(2):
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(fetch_g4f)
                response = future.result(timeout=30)
                
                chart_data = parse_chart_json(str(response))
                if chart_data and "labels" in chart_data and "values" in chart_data:
                    if len(chart_data["labels"]) == len(chart_data["values"]):
                        break
            except concurrent.futures.TimeoutError:
                continue
            except Exception as e:
                import time
                time.sleep(1)
                continue
                
        if not chart_data:
            return render(request, 'data_chart/data_chart.html', {
                'error': 'Failed to extract data for a chart. Ensure your text contains clear numerical associations.'
            })
            
        # Serialize to JSON string for JS
        chart_json_string = json.dumps(chart_data)
        
        deduct_credit(request.user)
        
        return render(request, 'data_chart/data_chart.html', {
            'success': True,
            'chart_data': chart_data,
            'chart_json_string': chart_json_string,
            'chart_type': chart_type
        })
        
    return render(request, 'data_chart/data_chart.html')
