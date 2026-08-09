import org.junit.Test;
import static org.junit.Assert.*;

public class GradeTest {

    @Test
    public void baseChoice_score75_returnsC() {
        assertEquals('C', Grade.letterGrade(75));
    }

    @Test
    public void gradeBand_score90_returnsA() {
        assertEquals('A', Grade.letterGrade(90));
    }

    @Test
    public void gradeBand_score80_returnsB() {
        assertEquals('B', Grade.letterGrade(80));
    }

    @Test
    public void gradeBand_score60_returnsD() {
        assertEquals('D', Grade.letterGrade(60));
    }

    @Test
    public void gradeBand_score0_returnsF() {
        assertEquals('F', Grade.letterGrade(0));
    }

    @Test
    public void rangeValidity_scoreBelowZero_throwsIllegalArgumentException() {
        try {
            Grade.letterGrade(-1);
            fail("Expected IllegalArgumentException to be thrown");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }

    @Test
    public void rangeValidity_scoreAboveHundred_throwsIllegalArgumentException() {
        try {
            Grade.letterGrade(101);
            fail("Expected IllegalArgumentException to be thrown");
        } catch (IllegalArgumentException e) {
            // expected
        }
    }
}