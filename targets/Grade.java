public class Grade {
    /**
     * Converts a numeric score (0-100) into a letter grade.
     * Boundaries: >=90 A, >=80 B, >=70 C, >=60 D, else F.
     * Throws IllegalArgumentException if score is outside 0-100.
     */
    public static char letterGrade(int score) {
        if (score < 0 || score > 100) {
            throw new IllegalArgumentException("score must be between 0 and 100");
        }
        if (score >= 90) return 'A';
        if (score >= 80) return 'B';
        if (score >= 70) return 'C';
        if (score >= 60) return 'D';
        return 'F';
    }
}
