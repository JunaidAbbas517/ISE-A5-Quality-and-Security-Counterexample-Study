# ISE-A5 Platform Result Summary

This study tried to falsify a security claim made by my Student Assignment and Deadline Management System (React +
Supabase): that the database enforces every role boundary, so the user interface does not need to be trusted. A copy
of the application at commit 417efd1 was hashed and left unchanged. Before any execution, I froze the protocol: the
environment (local PostgreSQL 16.2 with a minimal Supabase stand-in), the synthetic fixtures, 67 abuse, privilege,
boundary and fault-injection cases across eight actors, ten guard mutants, the oracle, the thresholds and a stopping
rule.

The baseline was valid, with all eleven controls passing, and identical over three runs. It falsified one sub-claim.
An instructor whose approval had been revoked could still rename, archive and delete their own course through the
REST API. Because the delete cascades, it removes every enrolled student's assignments, submissions and grades. The
interface hides these actions, but the database policies checked only ownership, not approval status. The other six
sub-claims were not falsified. The mutation score was 0.80, exactly at the threshold. One surviving mutant exposed a
test gap in the file-ownership check, and the other was effectively equivalent.

One bounded migration added the approved-instructor guard to two course policies. Rerunning the identical procedure
gave zero counterexamples, and all controls still passed, including re-approval. I also verified a rollback script.

The report discloses one harness deviation (a time-zone name), one weak case that passed for an unrelated reason, a
rejected suspected vulnerability, and the limits of the stand-in. Residual risks include the unpatched live project
and its public one-click test accounts. A recovery plan is provided. The repository contains the source, raw
results, an executed notebook, the report in Word and PDF, and an AI-use log.

## Repository URL

After pushing this folder to GitHub (suggested name `ISE-A5-Quality-and-Security-Counterexample-Study`) and tagging
it `ise-a5-v1.0`, submit the tag URL:
`https://github.com/JunaidAbbas517/ISE-A5-Quality-and-Security-Counterexample-Study/tree/ise-a5-v1.0`.
