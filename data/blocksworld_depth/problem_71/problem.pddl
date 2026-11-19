(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable orange)
		(on red orange)
		(on green red)
		(clear green)

		(ontable purple)
		(clear purple)
		(ontable yellow)
		(on blue yellow)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable blue)
		(clear blue)
		(ontable yellow)
		(on orange yellow)
		(clear orange)

		(ontable red)
		(on green red)
		(on purple green)
		(clear purple)
	))
)