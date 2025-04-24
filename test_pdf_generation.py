import unittest
import os
import tempfile
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from the app module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import generate_pdf_from_html

class TestPDFGeneration(unittest.TestCase):
    """Test cases for PDF generation functionality"""
    
    def test_basic_pdf_generation(self):
        """Test basic PDF generation with simple HTML content"""
        html_content = """
        <h1>Test PDF Generation</h1>
        <p>This is a test paragraph.</p>
        <h2>Section 1</h2>
        <p>This is content in section 1.</p>
        <h3>Subsection 1.1</h3>
        <p>This is a subsection with <strong>bold</strong> text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
            <li>Item 3</li>
        </ul>
        <h2>Section 2</h2>
        <p>This is content in section 2.</p>
        <ol>
            <li>First step</li>
            <li>Second step</li>
            <li>Third step</li>
        </ol>
        <table>
            <tr>
                <th>Header 1</th>
                <th>Header 2</th>
            </tr>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
            </tr>
            <tr>
                <td>Cell 3</td>
                <td>Cell 4</td>
            </tr>
        </table>
        <p><strong>Priority:</strong> High</p>
        <p><strong>Expected Impact:</strong> Significant cost reduction</p>
        """
        
        # Create a temporary file for the PDF output
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
        
        try:
            # Generate PDF using our function
            generate_pdf_from_html(html_content, pdf_path)
            
            # Check if the PDF file was created and is not empty
            self.assertTrue(os.path.exists(pdf_path), "PDF file was not created")
            self.assertGreater(os.path.getsize(pdf_path), 0, "PDF file is empty")
            
            print(f"PDF successfully generated at: {pdf_path}")
            print(f"PDF file size: {os.path.getsize(pdf_path)} bytes")
            
        finally:
            # Clean up - remove the temporary file
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

if __name__ == '__main__':
    unittest.main()