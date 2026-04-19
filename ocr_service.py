#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR Service using Google Cloud Vision API
Extracts text and structured data from loan application form images
"""

import os
import re
from datetime import datetime
from google.cloud import vision
from PIL import Image
import io

class OCRService:
    def __init__(self):
        """Initialize Google Cloud Vision client"""
        # Credentials should be set via GOOGLE_APPLICATION_CREDENTIALS env var
        self.client = vision.ImageAnnotatorClient()
    
    def extract_text_from_image(self, image_path):
        """
        Extract all text from an image using Google Cloud Vision
        
        Args:
            image_path: Path to the image file
            
        Returns:
            dict: Extracted text and confidence score
        """
        try:
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            
            # Perform text detection
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            
            if response.error.message:
                raise Exception(f'Google Vision API Error: {response.error.message}')
            
            if not texts:
                return {'text': '', 'confidence': 0}
            
            # First annotation contains all text
            full_text = texts[0].description
            
            return {
                'text': full_text,
                'confidence': texts[0].confidence if hasattr(texts[0], 'confidence') else 0.9,
                'blocks': [text.description for text in texts[1:]]  # Individual words/blocks
            }
            
        except Exception as e:
            print(f"OCR Error: {str(e)}")
            return {'text': '', 'confidence': 0, 'error': str(e)}
    
    def parse_dccco_form(self, text):
        """
        Parse DCCCO Multipurpose Cooperative form data
        
        Args:
            text: Raw text extracted from OCR
            
        Returns:
            dict: Structured data extracted from the form
        """
        data = {
            'applicant': {},
            'spouse': {},
            'family_background': [],
            'address': {},
            'income': {},
            'expenses': {},
            'assets': [],
            'liabilities': [],
            'co_maker': {},
            'references': []
        }
        
        lines = text.split('\n')
        
        # Extract applicant information
        data['applicant'] = self._extract_applicant_info(text, lines)
        
        # Extract spouse information
        data['spouse'] = self._extract_spouse_info(text, lines)
        
        # Extract family background
        data['family_background'] = self._extract_family_background(text, lines)
        
        # Extract address
        data['address'] = self._extract_address(text, lines)
        
        # Extract financial information
        data['income'] = self._extract_income(text, lines)
        data['expenses'] = self._extract_expenses(text, lines)
        data['assets'] = self._extract_assets(text, lines)
        data['liabilities'] = self._extract_liabilities(text, lines)
        
        # Extract co-maker
        data['co_maker'] = self._extract_co_maker(text, lines)
        
        # Extract references
        data['references'] = self._extract_references(text, lines)
        
        return data
    
    def _extract_applicant_info(self, text, lines):
        """Extract applicant personal information"""
        applicant = {
            'last_name': '',
            'first_name': '',
            'middle_name': '',
            'birthday': '',
            'age': ''
        }
        
        # Look for name fields
        for i, line in enumerate(lines):
            # Last Name
            if 'last name' in line.lower() and i + 1 < len(lines):
                applicant['last_name'] = self._clean_text(lines[i + 1])
            
            # First Name (look for JONA pattern from your image)
            if 'first name' in line.lower() and i + 1 < len(lines):
                applicant['first_name'] = self._clean_text(lines[i + 1])
            
            # Middle Name (look for RULANDA pattern)
            if 'middle name' in line.lower() and i + 1 < len(lines):
                applicant['middle_name'] = self._clean_text(lines[i + 1])
            
            # Birthday (look for 16/05/2000 pattern)
            if 'birthday' in line.lower() or 'birth' in line.lower():
                birthday = self._extract_date(lines[i:i+3])
                if birthday:
                    applicant['birthday'] = birthday
                    applicant['age'] = self._calculate_age(birthday)
        
        # Alternative: Use regex to find dates
        date_pattern = r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b'
        dates = re.findall(date_pattern, text)
        if dates and not applicant['birthday']:
            applicant['birthday'] = f"{dates[0][0]}/{dates[0][1]}/{dates[0][2]}"
            applicant['age'] = self._calculate_age(applicant['birthday'])
        
        return applicant
    
    def _extract_spouse_info(self, text, lines):
        """Extract spouse information"""
        spouse = {
            'last_name': '',
            'first_name': '',
            'middle_name': '',
            'birthday': '',
            'age': ''
        }
        
        # Look for spouse section
        spouse_section = False
        for i, line in enumerate(lines):
            if 'spouse' in line.lower():
                spouse_section = True
            
            if spouse_section:
                if 'last name' in line.lower() and i + 1 < len(lines):
                    spouse['last_name'] = self._clean_text(lines[i + 1])
                
                if 'first name' in line.lower() and i + 1 < len(lines):
                    spouse['first_name'] = self._clean_text(lines[i + 1])
                
                if 'middle name' in line.lower() and i + 1 < len(lines):
                    spouse['middle_name'] = self._clean_text(lines[i + 1])
                
                if 'birthday' in line.lower() or 'birth' in line.lower():
                    birthday = self._extract_date(lines[i:i+3])
                    if birthday:
                        spouse['birthday'] = birthday
                        spouse['age'] = self._calculate_age(birthday)
                
                # Stop at next major section
                if 'family background' in line.lower():
                    break
        
        return spouse
    
    def _extract_family_background(self, text, lines):
        """Extract family background table data"""
        family = []
        
        # Look for family background section
        in_family_section = False
        for i, line in enumerate(lines):
            if 'family background' in line.lower():
                in_family_section = True
                continue
            
            if in_family_section:
                # Look for table rows (name, age, relationship, member status)
                # Example: "Niza Curli    0    daughter    non-member"
                if line.strip() and not any(header in line.lower() for header in ['name', 'age', 'relationship', 'member']):
                    parts = line.split()
                    if len(parts) >= 3:
                        member = {
                            'name': ' '.join(parts[:-3]) if len(parts) > 3 else parts[0],
                            'age': parts[-3] if parts[-3].isdigit() else '',
                            'relationship': parts[-2],
                            'member_status': parts[-1]
                        }
                        family.append(member)
                
                # Stop at next section
                if any(keyword in line.lower() for keyword in ['address', 'income', 'residence']):
                    break
        
        return family
    
    def _extract_address(self, text, lines):
        """Extract address information"""
        address = {
            'purok': '',
            'barangay': '',
            'municipality': '',
            'province': '',
            'full_address': ''
        }
        
        # Look for address patterns
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['address', 'residence', 'purok', 'barangay']):
                # Get next few lines as address
                address_lines = lines[i:i+5]
                full_addr = ' '.join([l.strip() for l in address_lines if l.strip()])
                address['full_address'] = full_addr
                
                # Try to parse components
                if 'purok' in full_addr.lower():
                    purok_match = re.search(r'purok\s+(\d+|[a-z]+)', full_addr, re.IGNORECASE)
                    if purok_match:
                        address['purok'] = f"Purok {purok_match.group(1)}"
                
                # Common municipalities in Negros Oriental
                municipalities = ['bayawan', 'basay', 'sipalay', 'santa catalina']
                for muni in municipalities:
                    if muni in full_addr.lower():
                        address['municipality'] = muni.title()
                
                if 'negros oriental' in full_addr.lower():
                    address['province'] = 'Negros Oriental'
                
                break
        
        return address
    
    def _extract_income(self, text, lines):
        """Extract income information"""
        income = {
            'sources': [],
            'total': 0
        }
        
        # Look for income section
        in_income_section = False
        for i, line in enumerate(lines):
            if 'income' in line.lower() or 'salary' in line.lower():
                in_income_section = True
            
            if in_income_section:
                # Extract amounts (look for numbers with commas or decimals)
                amounts = re.findall(r'[\d,]+\.?\d*', line)
                for amount in amounts:
                    try:
                        value = float(amount.replace(',', ''))
                        if value > 0:
                            income['sources'].append({
                                'description': line.strip(),
                                'amount': value
                            })
                            income['total'] += value
                    except:
                        pass
                
                # Stop at expenses section
                if 'expense' in line.lower():
                    break
        
        return income
    
    def _extract_expenses(self, text, lines):
        """Extract expenses information"""
        expenses = {
            'items': [],
            'total': 0
        }
        
        # Look for expenses section
        in_expense_section = False
        for i, line in enumerate(lines):
            if 'expense' in line.lower():
                in_expense_section = True
            
            if in_expense_section:
                # Extract amounts
                amounts = re.findall(r'[\d,]+\.?\d*', line)
                for amount in amounts:
                    try:
                        value = float(amount.replace(',', ''))
                        if value > 0:
                            expenses['items'].append({
                                'description': line.strip(),
                                'amount': value
                            })
                            expenses['total'] += value
                    except:
                        pass
                
                # Stop at assets section
                if 'asset' in line.lower():
                    break
        
        return expenses
    
    def _extract_assets(self, text, lines):
        """Extract assets information"""
        assets = []
        
        in_asset_section = False
        for i, line in enumerate(lines):
            if 'asset' in line.lower():
                in_asset_section = True
            
            if in_asset_section:
                if line.strip() and not 'liabilit' in line.lower():
                    assets.append(line.strip())
                
                if 'liabilit' in line.lower():
                    break
        
        return assets
    
    def _extract_liabilities(self, text, lines):
        """Extract liabilities information"""
        liabilities = []
        
        in_liability_section = False
        for i, line in enumerate(lines):
            if 'liabilit' in line.lower():
                in_liability_section = True
            
            if in_liability_section:
                if line.strip() and not any(keyword in line.lower() for keyword in ['co-maker', 'reference']):
                    liabilities.append(line.strip())
                
                if 'co-maker' in line.lower() or 'reference' in line.lower():
                    break
        
        return liabilities
    
    def _extract_co_maker(self, text, lines):
        """Extract co-maker information"""
        co_maker = {
            'name': '',
            'address': '',
            'contact': ''
        }
        
        in_comaker_section = False
        for i, line in enumerate(lines):
            if 'co-maker' in line.lower() or 'comaker' in line.lower():
                in_comaker_section = True
                # Get next few lines
                if i + 1 < len(lines):
                    co_maker['name'] = lines[i + 1].strip()
                if i + 2 < len(lines):
                    co_maker['address'] = lines[i + 2].strip()
                if i + 3 < len(lines):
                    co_maker['contact'] = lines[i + 3].strip()
                break
        
        return co_maker
    
    def _extract_references(self, text, lines):
        """Extract references information"""
        references = []
        
        in_reference_section = False
        for i, line in enumerate(lines):
            if 'reference' in line.lower():
                in_reference_section = True
            
            if in_reference_section:
                if line.strip() and len(line.strip()) > 5:
                    references.append(line.strip())
                
                if len(references) >= 3:  # Usually 3 references
                    break
        
        return references
    
    def _clean_text(self, text):
        """Clean extracted text"""
        return text.strip().replace('\n', ' ').replace('  ', ' ')
    
    def _extract_date(self, lines):
        """Extract date from lines"""
        for line in lines:
            # Look for date pattern: DD/MM/YYYY or DD-MM-YYYY
            date_match = re.search(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b', line)
            if date_match:
                return f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
        return ''
    
    def _calculate_age(self, birthday_str):
        """Calculate age from birthday string"""
        try:
            # Parse date (DD/MM/YYYY)
            parts = birthday_str.split('/')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                birth_date = datetime(year, month, day)
                today = datetime.now()
                age = today.year - birth_date.year
                if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                    age -= 1
                return str(age)
        except:
            pass
        return ''
    
    def process_multiple_images(self, image_paths):
        """
        Process multiple images and combine extracted data
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            dict: Combined structured data from all images
        """
        combined_data = {
            'applicant': {},
            'spouse': {},
            'family_background': [],
            'address': {},
            'income': {},
            'expenses': {},
            'assets': [],
            'liabilities': [],
            'co_maker': {},
            'references': [],
            'raw_texts': []
        }
        
        for image_path in image_paths:
            result = self.extract_text_from_image(image_path)
            if result['text']:
                combined_data['raw_texts'].append(result['text'])
                parsed = self.parse_dccco_form(result['text'])
                
                # Merge data (prefer non-empty values)
                for key in ['applicant', 'spouse', 'address', 'income', 'expenses', 'co_maker']:
                    if parsed[key]:
                        for field, value in parsed[key].items():
                            if value and not combined_data[key].get(field):
                                combined_data[key][field] = value
                
                # Extend lists
                combined_data['family_background'].extend(parsed['family_background'])
                combined_data['assets'].extend(parsed['assets'])
                combined_data['liabilities'].extend(parsed['liabilities'])
                combined_data['references'].extend(parsed['references'])
        
        # Remove duplicates from lists
        combined_data['family_background'] = self._remove_duplicate_dicts(combined_data['family_background'])
        combined_data['assets'] = list(set(combined_data['assets']))
        combined_data['liabilities'] = list(set(combined_data['liabilities']))
        combined_data['references'] = list(set(combined_data['references']))
        
        return combined_data
    
    def _remove_duplicate_dicts(self, dict_list):
        """Remove duplicate dictionaries from list"""
        seen = set()
        unique = []
        for d in dict_list:
            t = tuple(sorted(d.items()))
            if t not in seen:
                seen.add(t)
                unique.append(d)
        return unique


# Singleton instance
_ocr_service = None

def get_ocr_service():
    """Get or create OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
