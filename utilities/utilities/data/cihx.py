# Test the functions directly without the command line interface
import xml.etree.ElementTree as ET
import os

def read_cihx_file(filename):
    """Read and extract XML content from CIHX file"""
    try:
        with open(filename, 'rb') as f:
            data = f.read()
        
        xml_start = data.find(b'<?xml')
        if xml_start == -1:
            print('No XML content found in ' + filename)
            return None
        
        xml_data = data[xml_start:].replace(b'\x00', b'').decode('utf-8', errors='ignore')
        xml_end = xml_data.rfind('</cih>')
        if xml_end != -1:
            xml_data = xml_data[:xml_end + 6]
        
        return xml_data
        
    except Exception as e:
        print('Error reading file ' + filename + ': ' + str(e))
        return None

# Version corrigée de la fonction parse_cihx_metadata avec frameInfo et recordInfo
def parse_cihx_metadata(xml_content):
    """Parse XML content and extract all metadata including frameInfo and recordInfo"""
    try:
        root = ET.fromstring(xml_content)
        metadata = {}
        
        # File information
        file_info = root.find('fileInfo')
        if file_info is not None:
            metadata['file_info'] = {}
            for child in file_info:
                metadata['file_info'][child.tag] = child.text
        
        # Image file information
        image_file_info = root.find('imageFileInfo')
        if image_file_info is not None:
            metadata['image_file_info'] = {}
            for child in image_file_info:
                if child.tag == 'resolution':
                    width = child.find('width')
                    height = child.find('height')
                    if width is not None and height is not None:
                        metadata['image_file_info']['resolution'] = width.text + 'x' + height.text
                else:
                    metadata['image_file_info'][child.tag] = child.text
        
        # Image data information
        image_data_info = root.find('imageDataInfo')
        if image_data_info is not None:
            metadata['image_data_info'] = {}
            
            resolution = image_data_info.find('resolution')
            if resolution is not None:
                width = resolution.find('width')
                height = resolution.find('height')
                if width is not None and height is not None:
                    metadata['image_data_info']['data_resolution'] = width.text + 'x' + height.text
            
            color_info = image_data_info.find('colorInfo')
            if color_info is not None:
                color_type = color_info.find('type')
                bit_depth = color_info.find('bit')
                if color_type is not None:
                    metadata['image_data_info']['color_type'] = color_type.text
                if bit_depth is not None:
                    metadata['image_data_info']['bit_depth'] = bit_depth.text
            
            effective_bit = image_data_info.find('effectiveBit')
            if effective_bit is not None:
                depth = effective_bit.find('depth')
                side = effective_bit.find('side')
                if depth is not None:
                    metadata['image_data_info']['effective_bit_depth'] = depth.text
                if side is not None:
                    metadata['image_data_info']['effective_bit_side'] = side.text
        
        # Frame information - AJOUT ICI
        frame_info = root.find('frameInfo')
        if frame_info is not None:
            metadata['frame_info'] = {}
            for child in frame_info:
                metadata['frame_info'][child.tag] = child.text
        
        # Record information - AJOUT ICI
        record_info = root.find('recordInfo')
        if record_info is not None:
            metadata['record_info'] = {}
            for child in record_info:
                # Gérer les éléments avec des sous-éléments
                if len(child) > 0:
                    metadata['record_info'][child.tag] = {}
                    for subchild in child:
                        metadata['record_info'][child.tag][subchild.tag] = subchild.text
                else:
                    metadata['record_info'][child.tag] = child.text
        
        return metadata
        
    except ET.ParseError as e:
        print('XML parsing error: ' + str(e))
        return None

if __name__ == "__main__":
    
    # Test
    filename = 'C:/Users/yberton/OneDrive - INSA Lyon/Scripts/Experimental/Visualisation et exploitation/Traitement caméra/examples/Pe_5.88_C001H001S0001/Pe_5.88_C001H001S0001.cihx'
    print('=== TESTING CIHX READER FUNCTIONS ===')
    print('File: ' + filename)
    print('File size: ' + str(os.path.getsize(filename)) + ' bytes')
    
    xml_content = read_cihx_file(filename)
    if xml_content:
        metadata = parse_cihx_metadata(xml_content)
        if metadata:
            print('=== METADATA COMPLET ===')
        
        if 'frame_info' in metadata:
            print('\
    Frame Information:')
            for key, value in metadata['frame_info'].items():
                print('  ' + key + ': ' + value)
        
        if 'record_info' in metadata:
            print('\
    Record Information:')
            for key, value in metadata['record_info'].items():
                if isinstance(value, dict):
                    print('  ' + key + ':')
                    for subkey, subvalue in value.items():
                        print('    ' + subkey + ': ' + subvalue)
                else:
                    print('  ' + key + ': ' + value)
        
        print('\
    Tous les metadata disponibles:')
        for section in metadata.keys():
            print('  - ' + section)