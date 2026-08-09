import org.junit.Test;
import static org.junit.Assert.*;

public class GradeTest {

    @Test
    public void testBaseChoiceGradeC() {
        assertEquals('C', Grade.letterGrade(75));
    }

    @Test(expected = IllegalArgumentException.class)
    public void testVariantScoreNegative() {
        Grade.letterGrade(-1);
    }

    @Test
    public void testVariantGradeF() {
        assertEquals('F', Grade.letterGrade(50));
    }

    @Test
    public void testVariantGradeD() {
        assertEquals('D', Grade.letterGrade(65));
    }

    @Test
    public void testVariantGradeB() {
        assertEquals('B', Grade.letterGrade(85));
    }

    @Test
    public void testVariantGradeA() {
        assertEquals('A', Grade.letterGrade(95));
    }

    @Test(expected = IllegalArgumentException.class)
    public void testVariantScoreAboveHundred() {
        Grade.letterGrade(105);
    }
}