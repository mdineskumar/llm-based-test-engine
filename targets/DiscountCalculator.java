public class DiscountCalculator {
    
    /**
     * Calculates the ticket discount percentage based on the customer's age.
     * 
     * Business Rules:
     * - Negative ages: return -1 (Invalid input error code)
     * - Ages 0 to 12 (inclusive): 50% discount
     * - Ages 65 and over (inclusive): 30% discount
     * - Ages 13 to 64: 0% discount
     */
    public static int getDiscount(int age) {
        // FAULT 1: Missing guard clause for negative ages. 
        // A negative age will incorrectly trigger this first if-statement and return 50.
        if (age <= 12) {
            return 50;
        }
        
        // FAULT 2: Off-by-one boundary error. 
        // The rule states 65 and over, but the code strictly requires greater than 65.
        // An age of exactly 65 will fall through and incorrectly receive a 0% discount.
        if (age > 65) {
            return 30;
        }
        
        return 0;
    }
}