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
		(ontable red)
		(on orange red)
		(on purple orange)
		(on blue purple)
		(clear blue)

		(ontable green)
		(clear green)
		(ontable yellow)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable orange)
		(on purple orange)
		(clear purple)
		(ontable green)
		(on red green)
		(clear red)
		(ontable yellow)
		(clear yellow)
		(ontable blue)
		(clear blue)
	))
)