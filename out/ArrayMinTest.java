import org.junit.Test;
import static org.junit.Assert.*;

public class ArrayMinTest {

    @Test
    public void testBaseChoice() {
        int[] arr = new int[]{2, 5, 8};
        assertEquals(2, ArrayMin.findMin(arr));
    }

    @Test(expected = IllegalArgumentException.class)
    public void testNullArray() {
        ArrayMin.findMin(null);
    }

    @Test(expected = IllegalArgumentException.class)
    public void testEmptyArray() {
        int[] arr = new int[]{};
        ArrayMin.findMin(arr);
    }

    @Test
    public void testSingleElementArray() {
        int[] arr = new int[]{5};
        assertEquals(5, ArrayMin.findMin(arr));
    }

    @Test
    public void testMinInMiddle() {
        int[] arr = new int[]{5, 2, 8};
        assertEquals(2, ArrayMin.findMin(arr));
    }

    @Test
    public void testMinAtEnd() {
        int[] arr = new int[]{5, 8, 2};
        assertEquals(2, ArrayMin.findMin(arr));
    }

    @Test
    public void testNegativeNumbers() {
        int[] arr = new int[]{-2, 5, 8};
        assertEquals(-2, ArrayMin.findMin(arr));
    }
}