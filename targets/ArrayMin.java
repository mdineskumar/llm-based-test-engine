public class ArrayMin {
    /**
     * Returns the minimum value in arr.
     * Throws IllegalArgumentException if arr is null or empty.
     */
    public static int findMin(int[] arr) {
        if (arr == null) {
            throw new IllegalArgumentException("array must not be null");
        }
        if (arr.length == 0) {
            throw new IllegalArgumentException("array must not be empty");
        }
        int min = arr[0];
        for (int i = 1; i < arr.length; i++) {
            if (arr[i] < min) {
                min = arr[i];
            }
        }
        return min;
    }
}
