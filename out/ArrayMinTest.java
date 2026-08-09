import org.junit.Test;
import static org.junit.Assert.*;

public class ArrayMinTest {

    @Test
    public void testBase_MultipleMixedMiddleNoDuplicate() {
        int[] arr = {5, 3, -8, 12, 6};
        assertEquals(-8, ArrayMin.findMin(arr));
    }

    @Test
    public void testNullArray_ThrowsException() {
        try {
            ArrayMin.findMin(null);
            fail("Expected IllegalArgumentException for null array");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    @Test
    public void testEmptyArray_ThrowsException() {
        try {
            ArrayMin.findMin(new int[] {});
            fail("Expected IllegalArgumentException for empty array");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    @Test
    public void testSingleElementArray() {
        int[] arr = {7};
        assertEquals(7, ArrayMin.findMin(arr));
    }

    @Test
    public void testMinAtFirstPosition() {
        int[] arr = {-9, 3, 8, 12, 6};
        assertEquals(-9, ArrayMin.findMin(arr));
    }

    @Test
    public void testMinAtLastPosition() {
        int[] arr = {5, 3, 8, 12, -9};
        assertEquals(-9, ArrayMin.findMin(arr));
    }

    @Test
    public void testDuplicateMinValue() {
        int[] arr = {5, -8, 3, -8, 6};
        assertEquals(-8, ArrayMin.findMin(arr));
    }

    @Test
    public void testAllPositiveValues() {
        int[] arr = {5, 3, 1, 12, 6};
        assertEquals(1, ArrayMin.findMin(arr));
    }

    @Test
    public void testAllNegativeValues() {
        int[] arr = {-5, -3, -8, -1, -6};
        assertEquals(-8, ArrayMin.findMin(arr));
    }
}