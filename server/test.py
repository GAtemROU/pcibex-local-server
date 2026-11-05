from pathlib import Path

# Input and output file paths
input_file = (
    Path(__file__).resolve().parents[1]
    / "ibex"
    / "results"
    / "experiment2"
    / "results"
)
output_file = "cleaned_results.csv"


import json

def convert_penncontroller_results(input_file, output_file, delimiter='\t', include_headers=True):
    """
    Convert PennController results format to line-by-line CSV/TSV.
    
    Format: [boolean, number, [headers], [data_rows]]
    Each data row: [[index, value], [index, value], ...]
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    try:
        # Parse the JSON
        data = json.loads(content)
        print(f"Successfully parsed JSON array with {len(data)} top-level elements")
        
        # Extract components
        boolean_flag = data[0]
        number_value = data[1] 
        headers = data[2]
        data_rows = data[3]
        
        print(f"Boolean flag: {boolean_flag}")
        print(f"Number value: {number_value}")
        print(f"Headers: {headers}")
        print(f"Data rows: {len(data_rows)}")
        
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        print(f"Error parsing data: {e}")
        return
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write headers if requested
        if include_headers:
            f.write(delimiter.join(headers) + '\n')
        
        # Process each data row
        for row in data_rows:
            # Create a dictionary to handle potentially unordered indices
            row_dict = {}
            
            # Extract values from [index, value] pairs
            for pair in row:
                if isinstance(pair, list) and len(pair) >= 2:
                    index = pair[0]
                    value = pair[1]
                    row_dict[index] = str(value)
            
            # Build output row in the correct order based on headers
            output_values = []
            for i in range(len(headers)):
                if i in row_dict:
                    output_values.append(row_dict[i])
                else:
                    output_values.append('')  # Empty string for missing values
            
            # Write the row
            f.write(delimiter.join(output_values) + '\n')
    
    print(f"Successfully converted {len(data_rows)} rows to {output_file}")
    
    # Return some stats
    return {
        'boolean_flag': boolean_flag,
        'number_value': number_value,
        'headers': headers,
        'total_rows': len(data_rows)
    }

def preview_penncontroller_data(input_file, num_rows=3):
    """
    Preview the PennController data structure.
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.readlines()
        for line in content:
            #data = ast.literal_eval(str(line))
            print(line)
    return
    try:
        data = ast.literal_eval(content)
        print(type(data))
        
        # print("=== PennController Data Structure ===")
        # print(f"Top-level elements: {len(data)}")
        # print(f"Boolean flag: {data[0]}")
        # print(f"Number value: {data[1]}")
        # print(f"Headers ({len(data[2])}): {data[2]}")
        # print(f"Data rows: {len(data[3])}")
        
        #print(f"\n=== Sample Data Rows (first {num_rows}) ===")
        for i, row in enumerate(data[3][:num_rows]):
            print(f"\nRow {i+1}:")
            for j, pair in enumerate(row):
                if isinstance(pair, list) and len(pair) >= 2:
                    header = data[2][pair[0]] if pair[0] < len(data[2]) else f"Index_{pair[0]}"
                    print(f"  {header}: '{pair[1]}'")
                else:
                    print(f"  Unexpected format: {pair}")
        
        # Check for any rows with duplicate indices (which might indicate issues)
        print(f"\n=== Data Quality Check ===")
        max_indices = []
        for row in data[3]:
            indices = [pair[0] for pair in row if isinstance(pair, list) and len(pair) >= 2]
            max_indices.append(max(indices) if indices else -1)
        
        print(f"Max column index found: {max(max_indices)}")
        print(f"Expected max index: {len(data[2]) - 1}")
        
        if max(max_indices) >= len(data[2]):
            print("WARNING: Some rows have indices beyond the header count!")
        
    except Exception as e:
        print(f"Error: {e}")

def convert_to_csv(input_file, output_file='results.csv'):
    """
    Convert to CSV format specifically.
    """
    return convert_penncontroller_results(input_file, output_file, delimiter=',', include_headers=True)

def convert_to_tsv(input_file, output_file='results.tsv'):
    """
    Convert to TSV format specifically.
    """
    return convert_penncontroller_results(input_file, output_file, delimiter='\t', include_headers=True)

# Example usage
if __name__ == "__main__":
    input_filename = input_file  # Your file
    
    # Preview the data first
    print("=== Previewing Data ===")
    preview_penncontroller_data(input_filename)
    
    # # Convert to different formats
    # print("\n=== Converting to TSV ===")
    # stats = convert_to_tsv(input_filename, 'results.tsv')
    
    # print("\n=== Converting to CSV ===")
    # convert_to_csv(input_filename, 'results.csv')
    
    # print("\n=== Conversion Complete ===")
    # print(f"Processed {stats['total_rows']} rows with {len(stats['headers'])} columns")
